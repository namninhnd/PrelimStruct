import sys
print("Starting...", file=sys.stderr, flush=True)

import openseespy.opensees as ops
print("OpenSeesPy imported", file=sys.stderr, flush=True)

ops.wipe()
ops.model('basic', '-ndm', 2, '-ndf', 3)

ops.node(1, 0.0, 0.0)
ops.node(2, 6.0, 0.0)

ops.fix(1, 1, 1, 1)
ops.fix(2, 1, 1, 1)

ops.geomTransf('Linear', 1)

E = 30e9
A = 0.18
I = 0.0054

ops.element('elasticBeamColumn', 1, 1, 2, A, E, I, 1)

w = 4410.0

ops.timeSeries('Linear', 1)
ops.pattern('Plain', 1, 1)
ops.eleLoad('-ele', 1, '-type', 'beamUniform', -w)
print("Model built", file=sys.stderr, flush=True)

ops.system('BandGeneral')
ops.numberer('RCM')
ops.constraints('Plain')
ops.integrator('LoadControl', 1.0)
ops.algorithm('Linear')
ops.analysis('Static')
print("Analysis setup", file=sys.stderr, flush=True)

result = ops.analyze(1)
print(f'Analysis result: {result}', file=sys.stderr, flush=True)

if result == 0:
    ops.reactions()
    R1 = ops.nodeReaction(1)
    R2 = ops.nodeReaction(2)
    print(f'R1 Fy={R1[1]/1000:.2f} kN, M={R1[2]/1000:.2f} kNm', file=sys.stderr, flush=True)
    print(f'R2 Fy={R2[1]/1000:.2f} kN, M={R2[2]/1000:.2f} kNm', file=sys.stderr, flush=True)
    print(f'Total Fy: {(R1[1]+R2[1])/1000:.2f} kN (expected: 26.46 kN)', file=sys.stderr, flush=True)
    
    forces = ops.eleForce(1)
    print(f'V_i={forces[1]/1000:.2f} kN, M_i={forces[2]/1000:.2f} kNm', file=sys.stderr, flush=True)
    print(f'V_j={forces[4]/1000:.2f} kN, M_j={forces[5]/1000:.2f} kNm', file=sys.stderr, flush=True)
    print(f'Expected V=13.23 kN, M=13.23 kNm (wL^2/12)', file=sys.stderr, flush=True)
