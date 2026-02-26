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
      rotate: {
        x: -0.5, // Tilt down to see from above
        y: 0.5,  // Rotate to see from angle
        z: 0,
      },
    });
    illoRef.current = illo;

    // Get drum color from name
    const getDrumColor = (drumName: string): string => {
      // Extract drum type from name (e.g., "BP_Kick_C" -> "Kick")
      const cleanName = drumName.replace('BP_', '').replace('_C', '');
      return DRUM_COLORS[cleanName] || '#64c8ff';
    };

    // Render each drum from the drum set
    mappingStore.drumSet.instruments.forEach((instrument) => {
      const pos = instrument.location || [0, 0, 0];
      const rot = instrument.rotation || [0, 0, 0];
      const scale = instrument.scale || [1, 1, 1];

      // Extract drum type for sizing
      const drumName = instrument.name.replace('BP_', '').replace('_C', '').replace(/_\d+$/, '');
      const color = getDrumColor(instrument.name);

      // Use scale from drum kit file for sizing
      // Base sizes (will be multiplied by scale)
      const baseSize = 30;
      const diameter = baseSize * scale[0];
      const length = baseSize * scale[2]; // Use Z scale for length/height

      // Create drum group with Unreal → Zdog coordinate mapping:
      // Unreal: X=Forward, Y=Right, Z=Up
      // Zdog: X=Right, Y=Down, Z=Depth
      const drumGroup = new Zdog.Group({
        addTo: illo,
        translate: {
          x: pos[1],  // Unreal Y (right) → Zdog X (right)
          y: -pos[2], // Unreal Z (up) → Zdog -Y (down, inverted)
          z: -pos[0], // Unreal X (forward) → Zdog -Z (depth, inverted for viewing)
        },
        rotate: {
          x: rot[0] * (Math.PI / 180) + Math.PI / 2, // Pitch + 90° to stand cylinders up
          y: rot[1] * (Math.PI / 180), // Yaw
          z: rot[2] * (Math.PI / 180), // Roll
        },
      });

      const isCymbal = drumName.includes('HiHat') || drumName.includes('Crash') || drumName.includes('Ride');

      if (isCymbal) {
        // Cymbals: Thin flat cylinders
        new Zdog.Cylinder({
          addTo: drumGroup,
          diameter: diameter,
          length: length,
          stroke: false,
          color: color,
          backface: color,
        });
      } else {
        // Drums: Standard cylinders
        new Zdog.Cylinder({
          addTo: drumGroup,
          diameter: diameter,
          length: length,
          stroke: false,
          color: color,
          backface: color,
        });
      }

      // Label (drum name)
      // Note: Zdog doesn't support text, so we'll skip labels for now
    });

    // Animation loop
    function animate() {
      illo.rotate.y += 0.003; // Slow auto-rotation
      illo.updateRenderGraph();
      requestAnimationFrame(animate);
    }
    animate();

    // Mouse drag controls
    let isRotating = false;
    let lastX = 0;
    let lastY = 0;

    const handleMouseDown = (e: MouseEvent) => {
      isRotating = true;
      lastX = e.clientX;
      lastY = e.clientY;
      canvas.style.cursor = 'grabbing';
    };

    const handleMouseMove = (e: MouseEvent) => {
      if (!isRotating) return;

      const deltaX = e.clientX - lastX;
      const deltaY = e.clientY - lastY;

      illo.rotate.y += deltaX * 0.01;
      illo.rotate.x += deltaY * 0.01;

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
        <canvas ref={canvasRef} className="block w-full h-[400px] cursor-grab" width={800} height={400} />

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
