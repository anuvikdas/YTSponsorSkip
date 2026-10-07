// Manual playback fixtures imported from the tune split of SponsorSkip_Validation.xlsx.
// They are disabled by default and are not detector output. Held-out and partial labels are excluded.
const DEVELOPMENT_FIXTURE_DELAY_MS = 1500;

const DEVELOPMENT_PLAYBACK_FIXTURES = Object.freeze({
  "094y1Z2wpJg": Object.freeze({ intervals: Object.freeze([{ startSeconds: 1248, endSeconds: 1327 }]) }),
  "bHIhgxav9LY": Object.freeze({ intervals: Object.freeze([{ startSeconds: 813, endSeconds: 882 }]) }),
  "iWeu2dxHRDg": Object.freeze({ intervals: Object.freeze([{ startSeconds: 1050, endSeconds: 1098 }]) }),
  "DTvS9lvRxZ8": Object.freeze({ intervals: Object.freeze([]) }),
  "I9hJ_Rux9y0": Object.freeze({ intervals: Object.freeze([]) }),
  "lXfEK8G8CUI": Object.freeze({ intervals: Object.freeze([{ startSeconds: 558, endSeconds: 645 }]) }),
  "-lErGZZgUbY": Object.freeze({ intervals: Object.freeze([{ startSeconds: 53, endSeconds: 74 }]) }),
  "MRtg6A1f2Ko": Object.freeze({ intervals: Object.freeze([{ startSeconds: 35, endSeconds: 104 }]) }),
  "9lx11dy9J30": Object.freeze({ intervals: Object.freeze([{ startSeconds: 903, endSeconds: 962 }]) }),
  "Sew4rctKghY": Object.freeze({ intervals: Object.freeze([{ startSeconds: 724, endSeconds: 788 }]) }),
  "O7sQBfpQCvU": Object.freeze({ intervals: Object.freeze([{ startSeconds: 565, endSeconds: 617 }]) }),
  "U3aXWizDbQ4": Object.freeze({ intervals: Object.freeze([]) }),
  "x7X9w_GIm1s": Object.freeze({ intervals: Object.freeze([]) }),
  "aircAruvnKk": Object.freeze({ intervals: Object.freeze([{ startSeconds: 992, endSeconds: 1023 }]) })
});

if (typeof module !== "undefined" && module.exports) {
  module.exports = { DEVELOPMENT_FIXTURE_DELAY_MS, DEVELOPMENT_PLAYBACK_FIXTURES };
} else {
  globalThis.DEVELOPMENT_FIXTURE_DELAY_MS = DEVELOPMENT_FIXTURE_DELAY_MS;
  globalThis.DEVELOPMENT_PLAYBACK_FIXTURES = DEVELOPMENT_PLAYBACK_FIXTURES;
}
