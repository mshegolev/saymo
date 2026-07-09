# F5 Natural Pacing Design

## Goal

Make the active F5 voice clone sound less rushed by combining text-level prosody hints with audio-level pacing.

## Approved Approach

Use both approved approaches:

- A: post-process F5 output by synthesizing natural chunks and inserting
  silence between them, including longer silent pauses where a person would
  take air before continuing.
- B: prepare punctuation before synthesis so high-confidence clause boundaries become explicit pause markers.

This does not retrain the model and does not modify user training data.

## Runtime Behavior

`F5TTSCloneTTS.synthesize()` will keep the same public API. Internally it will:

1. Normalize prosody punctuation for high-confidence boundaries.
2. Split text into sentence chunks, explicit `[pause:N]` markers, and paragraph breaks.
3. Synthesize only spoken chunks through the existing F5 CLI.
4. Join chunks into one WAV.
5. Insert configurable inter-sentence silence.
6. Insert longer silent breath pauses at paragraph breaks and occasional
   continuation points.

The live-call F5 path must not splice reference-sample breath audio into the
microphone output. The perceived breathing behavior is timing-only.

## Text Preparation

The primer should be conservative:

- Replace spaced em dashes with a short pause marker.
- Replace semicolon and non-time colon boundaries with a short pause marker.
- Keep commas as text, because inserting a pause after every comma makes Russian standup speech choppy.
- Preserve user-supplied `[pause:N]` markers.

## Testing

Automated tests will avoid real F5 inference. They will monkeypatch `_synthesize_sync()` to emit short WAV chunks, then assert:

- punctuation primer inserts pause markers only at intended boundaries;
- F5 synthesis is called per spoken chunk;
- final WAV contains silence between sentences;
- paragraph/continuation breaks can include a quiet non-zero breath segment;
- single-sentence synthesis remains close to the old path.

## Manual Verification

After tests pass, generate a short F5 preview and listen with `afplay`. Compare the old liked benchmark style against the new output, focusing on:

- pauses between sentences;
- pauses around dashes/colon/semicolon;
- breath continuity being barely perceptible, not noisy.
