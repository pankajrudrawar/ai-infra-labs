import subprocess, sys, glob
R=sys.argv[1]; out=sys.argv[2]
frames=sorted(glob.glob(R+'/frames/*.png'))
dur={'s-title':5,'s-summary':10,'s-arch-1':3.5,'s-arch-2':3.5,'s-arch-3':3.5,'s-arch-4':3.5,'s-arch-5':7,'s-steps':9,'s-sizing':13,'s-g1':11,'s-g2':11,'s-g3':11,'s-g4':11,'s-cost':9,'s-next':7}
names=[f.split('/')[-1][3:-4] for f in frames]
D=[dur[n] for n in names]
args=['ffmpeg','-y','-loglevel','error']
for f,d in zip(frames,D): args+=['-loop','1','-t',str(d),'-framerate','30','-i',f]
fc=[];prev='[0:v]';t=D[0]
for i in range(1,len(frames)):
    fd=0.4 if names[i].startswith('s-arch') and names[i]!='s-arch-1' else 0.7
    off=t-fd
    lab=f'[v{i}]'
    fc.append(f'{prev}[{i}:v]xfade=transition=fade:duration={fd}:offset={off:.2f}{lab}')
    prev=lab; t=off+D[i]
fc.append(f'{prev}fade=t=in:st=0:d=0.8,fade=t=out:st={t-1:.2f}:d=1,format=yuv420p[out]')
args+=['-filter_complex',';'.join(fc),'-map','[out]','-r','30','-c:v','libx264','-preset','slow','-crf','18','-movflags','+faststart',out]
subprocess.run(args,check=True); print('total',round(t,1),'s')
