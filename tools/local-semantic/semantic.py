"""Offline MiniLM prototype-margin experiment. No acquisition or hosted inference code."""

import hashlib
import json
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer
from views import build_views
from ytsponsorskip.detection_service import transcript_identity
from ytsponsorskip.detector import (
    DetectedInterval,
    DetectionResult,
    Sensitivity,
    validate_intervals,
)


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class LocalSemanticEncoder:
    def __init__(self, model_dir: Path, config: dict, cache_dir: Path):
        started = time.perf_counter()
        self.config = config
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.manifest = json.loads((model_dir / "manifest.json").read_text())
        if self.manifest["revision"] != config["revision"]:
            raise ValueError("Pinned model revision does not match downloaded assets")
        for name, record in self.manifest["files"].items():
            actual = hashlib.sha256((model_dir / name).read_bytes()).hexdigest()
            if actual != record["sha256"]:
                raise ValueError(f"Model asset hash mismatch: {name}")
        self.tokenizer = Tokenizer.from_file(str(model_dir / "tokenizer.json"))
        self.tokenizer.no_truncation()
        self.tokenizer.no_padding()
        options = ort.SessionOptions()
        options.intra_op_num_threads = 4
        options.inter_op_num_threads = 1
        options.log_severity_level = 3
        self.session = ort.InferenceSession(
            str(model_dir / "onnx/model.onnx"),
            sess_options=options,
            providers=["CPUExecutionProvider"],
        )
        self.input_names = {value.name for value in self.session.get_inputs()}
        self.load_ms = (time.perf_counter() - started) * 1000
        started = time.perf_counter()
        self.positive = self.encode(config["positive_prototypes"])
        self.negative = self.encode(config["negative_prototypes"])
        self.prototype_encoding_ms = (time.perf_counter() - started) * 1000

    def encode(self, texts):
        output = []
        for offset in range(0, len(texts), 16):
            batch = self.tokenizer.encode_batch(texts[offset : offset + 16])
            width = max(len(item.ids) for item in batch)
            if width > self.config["max_tokens_including_special"]:
                raise ValueError("Model input would exceed the frozen token bound")
            ids = np.zeros((len(batch), width), dtype=np.int64)
            mask = np.zeros_like(ids)
            types = np.zeros_like(ids)
            for position, item in enumerate(batch):
                ids[position, : len(item.ids)] = item.ids
                mask[position, : len(item.ids)] = item.attention_mask
                types[position, : len(item.ids)] = item.type_ids
            inputs = {"input_ids": ids, "attention_mask": mask, "token_type_ids": types}
            states = self.session.run(
                None, {key: value for key, value in inputs.items() if key in self.input_names}
            )[0]
            # Publisher-specified attention-mask mean pooling, followed by L2 normalization.
            pooled = (states * mask[..., None]).sum(axis=1) / np.maximum(
                mask.sum(axis=1, keepdims=True), 1
            )
            pooled /= np.maximum(np.linalg.norm(pooled, axis=1, keepdims=True), 1e-12)
            output.append(pooled.astype(np.float32))
        return np.concatenate(output)

    def score_transcript(self, transcript):
        started = time.perf_counter()
        windows, contexts = build_views(
            transcript,
            self.tokenizer,
            max_tokens=self.config["max_tokens_including_special"],
            overlap_tokens=self.config["target_overlap_tokens"],
        )
        views = windows + contexts
        source_hash = transcript_identity(transcript)
        cache_key = digest(
            {
                "transcript": source_hash,
                "model": self.manifest,
                "views": [asdict(view) for view in views],
                "encoder_source": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            }
        )
        cache_path = self.cache_dir / f"{cache_key}.npz"
        if cache_path.exists():
            with np.load(cache_path, allow_pickle=False) as saved:
                embeddings = saved["embeddings"]
            origin = "cached_local_embeddings"
        else:
            embeddings = self.encode([view.text for view in views])
            np.savez_compressed(cache_path, embeddings=embeddings)
            origin = "live_local_cpu_inference"
        if embeddings.shape != (len(views), 384) or not np.isfinite(embeddings).all():
            raise ValueError("Malformed local embedding output")
        positive = embeddings @ self.positive.T
        negative = embeddings @ self.negative.T
        rows = []
        for position, view in enumerate(views):
            pos_index = int(positive[position].argmax())
            neg_index = int(negative[position].argmax())
            pos_score = float(positive[position, pos_index])
            neg_score = float(negative[position, neg_index])
            rows.append(
                {
                    "snippet_indices": list(view.snippet_indices),
                    "context_indices": list(view.context_indices),
                    "token_count": view.token_count,
                    "positive_similarity": pos_score,
                    "negative_similarity": neg_score,
                    "margin": pos_score - neg_score,
                    "positive_prototype_index": pos_index,
                    "negative_prototype_index": neg_index,
                }
            )
        return {
            "video_id": transcript.video_id,
            "transcript_identity_sha256": source_hash,
            "embedding_cache_key": cache_key,
            "origin": origin,
            "encoding_and_scoring_ms": round((time.perf_counter() - started) * 1000, 3),
            "all_window_count": len(windows),
            "boundary_view_count": len(contexts),
            "source_cue_count": len(transcript.snippets),
            "covered_source_cue_count": len({i for view in windows for i in view.snippet_indices}),
            "max_encoded_tokens": max(view.token_count for view in views),
            "silent_truncation_count": 0,
            "windows": rows[: len(windows)],
            "boundary_contexts": rows[len(windows) :],
        }


class LocalSemanticDetector:
    def __init__(self, evidence_by_id, *, threshold, minimum_similarity):
        self.evidence = evidence_by_id
        self.threshold = threshold
        self.minimum_similarity = minimum_similarity

    def detect(self, transcript, sensitivity=Sensitivity.CONSERVATIVE):
        evidence = self.evidence[transcript.video_id]
        if transcript_identity(transcript) != evidence["transcript_identity_sha256"]:
            raise ValueError("Semantic evidence does not match exact source transcript")

        def qualifies(row):
            return (
                row["positive_similarity"] >= self.minimum_similarity
                and row["margin"] >= self.threshold
            )

        exposed = {
            index
            for row in evidence["windows"]
            if qualifies(row)
            for index in row["snippet_indices"]
        }
        supported = {
            index
            for row in evidence["boundary_contexts"]
            if qualifies(row)
            for index in row["snippet_indices"]
        }
        intervals = [
            DetectedInterval(
                cue.start_seconds,
                cue.end_seconds,
                round(self.threshold * 1000),
                ("local_semantic_prototype_margin",),
                (cue.index,),
            )
            for cue in transcript.snippets
            if cue.index in exposed & supported
        ]
        return DetectionResult(
            transcript.video_id,
            sensitivity,
            validate_intervals(intervals),
            evidence["all_window_count"],
        )
