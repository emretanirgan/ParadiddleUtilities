import { useEffect, useRef } from 'react';
import Zdog from 'zdog';
import { useMappingStore } from '../stores/mapping-store';
import { DRUM_COLORS } from '../visualization/piano-roll-renderer';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface DrumKitVisualizerProps {
  onClose: () => void;
}

export function DrumKitVisualizer({ onClose }: DrumKitVisualizerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const illoRef = useRef<Zdog.Illustration | null>(null);
  const mappingStore = useMappingStore();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !mappingStore.drumSet) {
      return;
    }

    // Create Zdog illustration
    const illo = new Zdog.Illustration({
      element: canvas,
      dragRotate: true,
      resize: true,
      zoom: 1.25,
      rotate: {
        x: -0.5, // Tilt down to see from above
        // y: 0.5,  // Rotate to see from angle
        // z: 0,
      },
      translate: {
        x: 0,
        y: 40,
        z: 0,
      },
    });
    illoRef.current = illo;

    // Get drum color from name
    const getDrumColor = (drumName: string): string => {
      // Extract drum type from name (e.g., "BP_Kick_C" -> "Kick")
      const cleanName = drumName.split('_')[1] || drumName; // Fallback to full name if unexpected format
      console.log('Determining color for drum:', drumName, '->', cleanName);

      return DRUM_COLORS[cleanName] || '#64c8ff';
    };

      // Add a flat plane for ground reference
      new Zdog.Rect({
        addTo: illo,
        width: 200,
        height: 200,
        stroke: false,
        fill: true,
        color: '#ccc',
        backface: '#eee',
        translate: { y: 20 },
        rotate: { x: Math.PI / 2 },
      });

    // Render each drum from the drum set
    mappingStore.drumSet.instruments.forEach((instrument) => {
      const pos = instrument.location || [0, 0, 0];
      const rot = instrument.rotation || [0, 0, 0];
      const scale = instrument.scale || [1, 1, 1];

      // Extract drum type for sizing
      const drumName = instrument.name.replace('BP_', '').replace('_C', '').replace(/_\d+$/, '');
      const color = getDrumColor(instrument.name);
      // if (!drumName.includes('Kick')) { return; } // TEMP: Only render snares for now, to focus on debugging orientation/sizing
      // Use scale from drum kit file for sizing
      // Base sizes (will be multiplied by scale)
      const baseSize = 30;
      const diameter = baseSize * scale[0];
      const length = baseSize * scale[2]; // Use Z scale for length/height

      // Convert Unreal FRotator → Zdog {x,y,z} Euler angles.
      //
      // Step 1: FRotator (Pitch, Yaw, Roll) → quaternion using Unreal's source formula.
      // Step 2: Remap quaternion axes to Zdog frame:
      //   Unreal X=fwd → Zdog -Z:  qx_z = -qx_u
      //   Unreal Y=right → Zdog +X: qx_z =  qy_u  (overwrites — see below)
      //   Unreal Z=up → Zdog -Y:   qy_z = -qz_u
      //   Full remap: qx_z = qy_u,  qy_z = -qz_u,  qz_z = -qx_u,  qw_z = qw_u
      // Step 3: Extract ZYX Tait-Bryan Euler angles from the remapped quaternion
      //   (ZYX matches Zdog's apply order: rotateZ first, then Y, then X).
      // Step 4: Negate the Y angle — Zdog's rotateY matrix is the transpose of standard RH Ry,
      //   equivalent to Ry(-θ), so the extracted standard angle must be negated.
      console.log(`Adding drum: ${drumName}, pos: ${pos}, rot: ${rot}, scale: ${scale}, color: ${color}`);
      const halfDeg = Math.PI / 360;
      const sp = Math.sin(rot[0] * halfDeg), cp = Math.cos(rot[0] * halfDeg); // Pitch
      const sy = Math.sin(rot[1] * halfDeg), cy = Math.cos(rot[1] * halfDeg); // Yaw
      const sr = Math.sin(rot[2] * halfDeg), cr = Math.cos(rot[2] * halfDeg); // Roll

      // Unreal FQuat (from UE source FRotator::Quaternion())
      const qxU =  cr*sp*sy - sr*cp*cy;
      const qyU = -cr*sp*cy - sr*cp*sy;
      const qzU =  cr*cp*sy - sr*sp*cy;
      const qwU =  cr*cp*cy + sr*sp*sy;

      // Remap to Zdog frame
      const qx = qyU, qy = -qzU, qz = -qxU, qw = qwU;

      // Extract ZYX Tait-Bryan Euler angles (R = Rx * Ry_std * Rz)
      const rx =  Math.atan2(2*(qw*qx + qy*qz), 1 - 2*(qx*qx + qy*qy));
      const ry =  Math.asin(Math.max(-1, Math.min(1, 2*(qw*qy - qz*qx))));
      const rz =  Math.atan2(2*(qw*qz + qx*qy), 1 - 2*(qy*qy + qz*qz));

      const drumGroup = new Zdog.Group({
        addTo: illo,
        translate: {
          x:  pos[1],  // Unreal Y (right)  → Zdog X
          y: -pos[2],  // Unreal Z (up)      → Zdog -Y
          z: -pos[0],  // Unreal X (forward) → Zdog -Z
        },
        rotate: { x: rx, y: -ry, z: rz }, // negate ry for Zdog's non-standard rotateY
      });

      // Zdog cylinders/cones point along Z; drums in the kit point along world up (Zdog -Y).
      // A +π/2 rotation around X maps Z → -Y.
      const shapeGroup = new Zdog.Group({ addTo: drumGroup, rotate: { x: Math.PI / 2 } });

      const isCymbal = drumName.includes('HiHat') || drumName.includes('Crash') || drumName.includes('Ride');

      if (isCymbal) {
        // Cymbals: Cones (Zdog typings are missing Cone, cast to any)
        new (Zdog as any).Cone({
          addTo: shapeGroup,
          diameter: diameter,
          length: length/3,
          stroke: false,
          color: color,
          backface: color,
          frontface: color,
        });
      } else {
        // Drums: Standard cylinders — colored drumhead on frontface, neutral shell
        new (Zdog as any).Cylinder({
          addTo: shapeGroup,
          diameter: diameter,
          length: length/1.5,
          stroke: false,
          color: '#444',
          frontface: color,
          backface: color,
        });
      }



      // Label (drum name)
      // Note: Zdog doesn't support text, so we'll skip labels for now
    });

    // Animation loop
    function animate() {
      // illo.rotate.y += 0.003; // Slow auto-rotation
      illo.updateRenderGraph();
      requestAnimationFrame(animate);
    }
    animate();

    // Mouse drag controls
    let isRotating = false;
    let lastX = 0;
    let lastY = 0;

    const handleMouseDown = (e: MouseEvent) => {
      // isRotating = true;
      lastX = e.clientX;
      // lastY = e.clientY;
      canvas.style.cursor = 'grabbing';
    };

    const handleMouseMove = (e: MouseEvent) => {
      if (!isRotating) return;

      const deltaX = e.clientX - lastX;
      // const deltaY = e.clientY - lastY;

      illo.rotate.y += deltaX * 0.01;
      // illo.rotate.x += deltaY * 0.01;

      lastX = e.clientX;
      lastY = e.clientY;
    };

    const handleMouseUp = () => {
      isRotating = false;
      canvas.style.cursor = 'grab';
    };

    canvas.addEventListener('mousedown', handleMouseDown);
    canvas.addEventListener('mousemove', handleMouseMove);
    canvas.addEventListener('mouseup', handleMouseUp);
    canvas.addEventListener('mouseleave', handleMouseUp);

    // Cleanup
    return () => {
      canvas.removeEventListener('mousedown', handleMouseDown);
      canvas.removeEventListener('mousemove', handleMouseMove);
      canvas.removeEventListener('mouseup', handleMouseUp);
      canvas.removeEventListener('mouseleave', handleMouseUp);
    };
  }, [mappingStore.drumSet]);

  const handleResetView = () => {
    if (illoRef.current) {
      illoRef.current.rotate.x = -0.5;
      illoRef.current.rotate.y = 0.5;
      illoRef.current.rotate.z = 0;
    }
  };

  if (!mappingStore.drumSet) {
    return (
      <Card className="mt-4">
        <CardContent className="pt-6">
          <p className="text-muted-foreground">No drum set loaded</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="mt-4">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
        <CardTitle>3D Drum Kit Preview</CardTitle>
        <Button variant="secondary" size="sm" onClick={onClose}>
          Close
        </Button>
      </CardHeader>
      <CardContent>
        <canvas ref={canvasRef} className="block w-full h-[400px] cursor-grab" width={800} height={300} />

        <div className="mt-4 flex items-center gap-2 text-sm text-muted-foreground">
          <Button size="sm" onClick={handleResetView}>
            Reset View
          </Button>
          <span className="text-xs text-muted-foreground">
            Drag to rotate &bull; {mappingStore.drumSet.instruments.length} instruments
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
