// AudioWorklet processor for the Chat voice feature (docs/todo/
// voice-chat-poc-implementation-plan.md T13). Runs on the audio
// rendering thread, not the main thread -- unlike the throwaway
// ScriptProcessorNode used in tools/voice-test-page/index.html, this is
// the modern, non-deprecated API, appropriate for real product code.
//
// Downsamples the mic's native sample rate (typically 44100/48000) to
// 16000 Hz mono 16-bit PCM, matching apps/api/app/core/settings.py's
// `deepgram_sample_rate` default, and posts each resulting buffer back
// to the main thread over `port`. If that backend setting ever changes,
// the `targetSampleRate` processorOption passed from the main thread
// must change too -- there is no runtime negotiation of this value.
//
// Not bundled/transpiled -- served as-is from apps/web/public/, loaded
// via `audioContext.audioWorklet.addModule('/voice-worklet.js')`. Must
// stay plain, dependency-free JS for that reason.

class VoiceDownsampleProcessor extends AudioWorkletProcessor {
  constructor(options) {
    super();
    const opts = (options && options.processorOptions) || {};
    this.targetSampleRate = opts.targetSampleRate || 16000;
    // `sampleRate` is a global in AudioWorkletGlobalScope -- the
    // AudioContext's actual native rate.
    this.ratio = sampleRate / this.targetSampleRate;
    this.pending = [];
    // Batch into ~100ms-of-output-audio chunks before posting, so the
    // main thread isn't flooded with a message per 128-sample block.
    this.samplesPerBatch = Math.floor(this.targetSampleRate * 0.1 * this.ratio);
  }

  process(inputs) {
    const channel = inputs[0] && inputs[0][0];
    if (channel) {
      for (let i = 0; i < channel.length; i++) {
        this.pending.push(channel[i]);
      }

      while (this.pending.length >= this.samplesPerBatch) {
        const batch = this.pending.splice(0, this.samplesPerBatch);
        const outLength = Math.floor(batch.length / this.ratio);
        const pcm16 = new Int16Array(outLength);
        for (let i = 0; i < outLength; i++) {
          const sample = Math.max(-1, Math.min(1, batch[Math.floor(i * this.ratio)]));
          pcm16[i] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
        }
        this.port.postMessage(pcm16.buffer, [pcm16.buffer]);
      }
    }

    return true; // keep the processor alive for the life of the node
  }
}

registerProcessor('voice-downsample-processor', VoiceDownsampleProcessor);
