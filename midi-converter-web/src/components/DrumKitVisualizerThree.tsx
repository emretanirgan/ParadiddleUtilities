import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { useMappingStore } from '../stores/mapping-store';
import { DRUM_COLORS } from '../visualization/piano-roll-renderer';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

// Converts an Unreal FRotator [pitch, yaw, roll] (degrees) to a Three.js Quaternion.
// Uses the scalar path from UE source (FRotator3f::Quaternion()), then remaps axes:
//   Unreal (LH, X=fwd, Y=right, Z=up) → Three.js (RH, X=right, Y=up, Z=toward viewer)
// The coordinate transform has det=-1 (LH→RH), so the quaternion vector part is negated
// after axis remapping: qx=-qyU, qy=-qzU, qz=qxU, qw=qwU.
function unrealRotatorToThreeQuaternion(pitch: number, yaw: number, roll: number): THREE.Quaternion {
  const halfDeg = Math.PI / 360;
  const sp = Math.sin(pitch * halfDeg), cp = Math.cos(pitch * halfDeg);
  const sy = Math.sin(yaw   * halfDeg), cy = Math.cos(yaw   * halfDeg);
  const sr = Math.sin(roll  * halfDeg), cr = Math.cos(roll  * halfDeg);

  // UE scalar formula (FRotator3f::Quaternion, non-SIMD path)
  const qxU =  cr*sp*sy - sr*cp*cy;
  const qyU = -cr*sp*cy - sr*cp*sy;
  const qzU =  cr*cp*sy - sr*sp*cy;
  const qwU =  cr*cp*cy + sr*sp*sy;
  console.log(`UE FRotator (pitch, yaw, roll): (${pitch}, ${yaw}, ${roll}) → FQuat (qx, qy, qz, qw): (${qxU}, ${qyU}, ${qzU}, ${qwU})`);
  // Remap to Three.js frame: negate vector part, then apply axis mapping
  return new THREE.Quaternion(-qyU, qzU, -qxU, qwU).normalize();
}

interface DrumKitVisualizerThreeProps {
  onClose: () => void;
}

export function DrumKitVisualizerThree({ onClose }: DrumKitVisualizerThreeProps) {
  const mountRef = useRef<HTMLDivElement>(null);
  const mappingStore = useMappingStore();

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount || !mappingStore.drumSet) return;

    const width = mount.clientWidth;
    const height = 400;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0f172a);

    const axesHelper = new THREE.AxesHelper( 20 ); 
    scene.add( axesHelper );

    // const camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 5000);
    const camera = new THREE.OrthographicCamera(-width / 4, width / 4, height / 4, -height / 4, 0.1, 5000);
    camera.position.set(250, 200, 250);
    camera.lookAt(0, 50, 0);

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(window.devicePixelRatio);
    mount.appendChild(renderer.domElement);

    scene.add(new THREE.AmbientLight(0xffffff, 0.6));
    const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
    dirLight.position.set(100, 200, 100);
    scene.add(dirLight);

    const getDrumColor = (name: string): number => {
      const cleanName = name.replace('BP_', '').replace('_C', '').replace(/_\d+$/, '');
      const hex = DRUM_COLORS[cleanName] || '#64c8ff';
      return parseInt(hex.replace('#', ''), 16);
    };

    mappingStore.drumSet.instruments.forEach((instrument) => {
      // if (!instrument.name.includes('Kick')) { return; } // TEMP: Only render kicks for now, to focus on debugging orientation/sizing
      const pos = instrument.location || [0, 0, 0];
      const rot = instrument.rotation || [0, 0, 0];
      const scale = instrument.scale || [1, 1, 1];

      const drumName = instrument.name.replace('BP_', '').replace('_C', '').replace(/_\d+$/, '');
      const baseSize = 30;
      const radius = (baseSize * scale[0]) / 2;
      const length = baseSize * scale[2];
      const isCymbal = drumName.includes('HiHat') || drumName.includes('Crash') || drumName.includes('Ride');

      // Position: Unreal (X=fwd, Y=right, Z=up) → Three.js (X=right, Y=up, Z=-fwd)
      const position = new THREE.Vector3(pos[1], pos[2], -pos[0]);
      const quaternion = unrealRotatorToThreeQuaternion(rot[1], rot[2], rot[0]);
      console.log('Drum:', instrument.name, 'Position:', position, 'Rotation (Euler):', rot, 'Quaternion:', quaternion);
      const color = getDrumColor(instrument.name);
      const mat = new THREE.MeshLambertMaterial({ color });

      let geo: THREE.BufferGeometry;
      if (isCymbal) {
        // ConeGeometry axis is along Y by default — points up, matching Unreal Z(up) after coord mapping
        geo = new THREE.ConeGeometry(radius, length / 3, 32);
      } else {
        // CylinderGeometry axis is along Y by default — no orientation correction needed
        geo = new THREE.CylinderGeometry(radius, radius, length / 1.5, 32);
      }

      const mesh = new THREE.Mesh(geo, mat);
      mesh.position.copy(position);
      mesh.quaternion.copy(quaternion);
      scene.add(mesh);
    });

    // Slow orbit around the kit
    let angle = Math.PI / 4;
    let animFrameId: number;
    function animate() {
      animFrameId = requestAnimationFrame(animate);
      angle += 0.003;
      camera.position.set(250 * Math.sin(angle), 200, 250 * Math.cos(angle));
      camera.lookAt(0, 50, 0);
      renderer.render(scene, camera);
    }
    animate();

    return () => {
      cancelAnimationFrame(animFrameId);
      mount.removeChild(renderer.domElement);
      renderer.dispose();
    };
  }, [mappingStore.drumSet]);

  if (!mappingStore.drumSet) return null;

  return (
    <Card className="mt-4">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
        <CardTitle>3D Drum Kit Preview (Three.js)</CardTitle>
        <Button variant="secondary" size="sm" onClick={onClose}>
          Close
        </Button>
      </CardHeader>
      <CardContent>
        <div ref={mountRef} className="w-full h-[400px]" />
      </CardContent>
    </Card>
  );
}
