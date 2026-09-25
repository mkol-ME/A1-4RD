#!/usr/bin/env python3
"""Explicit, low-level test tone + microphone capture. Does not move the servo.

Produces a short 1 kHz tone at -30 dBFS and a local microphone recording.
Pass --device hw:CARDNAME,0 from arecord -l / aplay -l. One client per direction.
Tests both startup orders; return success proves process completion, not sound quality.
"""
import argparse, math, pathlib, shutil, struct, subprocess, tempfile, time, wave

def make_tone(path, seconds=3):
    with wave.open(str(path), 'wb') as f:
        f.setparams((2, 4, 48000, 0, 'NONE', 'not compressed'))
        gain=10**(-30/20)
        f.writeframes(b''.join(struct.pack('<ii', *(2*[int((2**31-1)*gain*math.sin(2*math.pi*1000*i/48000))])) for i in range(seconds*48000)))

def run(device, order, out, tone):
    capture=['arecord','-D',device,'-f','S32_LE','-r','48000','-c','2','-d','5',str(out/f'{order}.wav')]
    playback=['aplay','-D',device,str(tone)]
    commands=[capture,playback] if order=='capture-first' else [playback,capture]
    jobs=[]; logs=[]
    try:
        for i,command in enumerate(commands):
            log=(out/f'{order}-{i}.log').open('wb');logs.append(log)
            jobs.append(subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT))
            if i==0:
                time.sleep(.5)
                if jobs[0].poll() is not None:raise RuntimeError('First stream stopped before the second started; inspect logs.')
        for process in jobs:
            if process.wait(timeout=12):raise RuntimeError(f'{order}: audio process failed; inspect logs.')
    finally:
        for process in jobs:
            if process.poll() is None:process.terminate()
        for process in jobs:
            try:process.wait(timeout=2)
            except subprocess.TimeoutExpired:process.kill();process.wait()
        for log in logs:log.close()
    for file in out.glob(f'{order}-*.log'):
        text=file.read_text(errors='replace').lower()
        if any(term in text for term in ('underrun','overrun','xrun')):raise RuntimeError(f'Audio timing error: {file}')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device',required=True)
    parser.add_argument('--output',type=pathlib.Path,default=pathlib.Path('alfred-audio-test'))
    args=parser.parse_args()
    for name in ['arecord','aplay']:
        if not shutil.which(name):parser.error(f'{name} missing; install alsa-utils')
    # Do not overwrite recordings from an earlier test.
    args.output.mkdir(parents=True,exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='alfred-tone-') as tmp:
        tone=pathlib.Path(tmp)/'tone.wav';make_tone(tone)
        for order in ['capture-first','playback-first']:run(args.device,order,args.output,tone)
    print('Both stream orders completed. Inspect recordings for a live left microphone channel, tone and clipping.')
    print('Still required: 30-minute full-duplex load test, clock measurement, power and acoustic tests.')

if __name__=='__main__':main()
