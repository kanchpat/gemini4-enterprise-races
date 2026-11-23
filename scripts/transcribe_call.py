"""Timestamped transcript of the Q3 2026 call (prepared remarks), in 4-minute clips.

Short clips keep model timestamps reliable; each clip's times are relative to the
clip start and the clip offset is added here. Output: /tmp/p2/call_transcript.json
"""
import concurrent.futures as cf, json, os, sys
sys.path.insert(0, os.path.expanduser('~/gemini4-enterprise-races/races'))
import common

MODEL = sys.argv[1] if len(sys.argv) > 1 else 'gemini-4-hydrogen'
URL = 'https://www.youtube.com/watch?v=X9mmCagxJTo'
END, STEP = 2026, 240
PROMPT = ('Transcribe this clip of an earnings call verbatim. Return JSON: '
          '{"segments":[{"t":<seconds from the START OF THIS CLIP, number>,"speaker":"<name or role if said>","text":"<one sentence>"}]}. '
          'One sentence per segment, in order. Keep every number exactly as spoken.')


def clip(a):
  b = min(a + STEP, END)
  part = {'fileData': {'fileUri': URL, 'mimeType': 'video/*'},
          'videoMetadata': {'startOffset': f'{a}s', 'endOffset': f'{b}s'}}
  r = common.generate(MODEL, [part, {'text': PROMPT}], thinking='LOW', json_mode=True,
                      media_resolution='MEDIA_RESOLUTION_LOW', max_output_tokens=16000)
  if r.error:
    return a, {'error': r.error}
  segs = common.parse_json(r.text)['segments']
  for s in segs:
    s['t'] = round(a + float(s['t']), 1)
  return a, {'segments': segs, 'cost': r.cost_list_usd}


with cf.ThreadPoolExecutor(9) as ex:
  res = dict(ex.map(clip, range(0, END, STEP)))
out, cost = [], 0
for a in sorted(res):
  if 'error' in res[a]:
    print('ERR', a, res[a]['error'][:200]); continue
  out += res[a]['segments']; cost += res[a]['cost']
os.makedirs('/tmp/p2', exist_ok=True)
json.dump(out, open(f'/tmp/p2/call_transcript_{MODEL}.json', 'w'), indent=1)
print(len(out), 'segments', f'${cost:.2f}')
