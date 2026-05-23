import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { useMappingStore } from '../stores/mapping-store';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

const CM_TO_M = 0.01;

// Confirmed working position mapping:
// Unreal [x, y, z] -> Three [y, z, -x]
const BASIS_CHANGE = new THREE.Matrix4().set(
   0, 1,  0, 0,
   0, 0,  1, 0,
  -1, 0,  0, 0,
   0, 0,  0, 1
);
const BASIS_CHANGE_INV = BASIS_CHANGE.clone().invert();

function degToRad(deg: number): number {
  return THREE.MathUtils.degToRad(deg);
}

function isHiHatClass(className: string) { return className.includes('HiHat'); }
function isKickClass(className: string)  { return className.includes('Kick'); }
function isSnareClass(className: string) { return className.includes('Snare'); }
function isFloorTomClass(className: string) { return className.includes('FloorTom'); }
function isTomClass(className: string)   { return className.includes('Tom'); }
function isCymbalClass(className: string) {
  return className.includes('Crash') || className.includes('Ride') || className.includes('HiHat');
}

function createGeometryForInstrument(className: string): THREE.BufferGeometry {
  if (isKickClass(className))      return new THREE.CylinderGeometry(0.28, 0.28, 0.45, 32);
  if (isSnareClass(className))     return new THREE.CylinderGeometry(0.18, 0.18, 0.12, 32);
  if (isFloorTomClass(className))  return new THREE.CylinderGeometry(0.22, 0.22, 0.16, 32);
  if (isTomClass(className))       return new THREE.CylinderGeometry(0.16, 0.16, 0.14, 32);
  if (isHiHatClass(className))     return new THREE.ConeGeometry(0.20, 0.03, 32, 1, true);
  if (className.includes('Crash')) return new THREE.ConeGeometry(0.24, 0.035, 32, 1, true);
  if (className.includes('Ride'))  return new THREE.ConeGeometry(0.26, 0.035, 32, 1, true);
  return new THREE.BoxGeometry(0.1, 0.1, 0.1);
}

function createMaterialForInstrument(className: string): THREE.MeshLambertMaterial {
  if (isCymbalClass(className)) return new THREE.MeshLambertMaterial({ color: 0xd6b24c, side: THREE.DoubleSide });
  if (isKickClass(className))   return new THREE.MeshLambertMaterial({ color: 0x2b2b2b });
  if (isSnareClass(className))  return new THREE.MeshLambertMaterial({ color: 0xbfc3c9 });
  return new THREE.MeshLambertMaterial({ color: 0x7a4a25 });
}

function unrealLocationToThree(location: number[]): THREE.Vector3 {
  const [x, y, z] = location;
  return new THREE.Vector3(y * CM_TO_M, z * CM_TO_M, -x * CM_TO_M);
}

function unrealScaleToThree(scale: number[] | undefined): THREE.Vector3 {
  const [sx, sy, sz] = scale ?? [1, 1, 1];
  return new THREE.Vector3(sy, sz, sx);
}

// Rotation array format from .rlrr: [roll, pitch, yaw]
function rotationArrayToUnrealQuat(rotationArray: number[]): THREE.Quaternion {
  const [rollDeg, pitchDeg, yawDeg] = rotationArray;

  const yaw   = new THREE.Matrix4().makeRotationZ(degToRad(yawDeg));
  const pitch = new THREE.Matrix4().makeRotationY(degToRad(pitchDeg));
  const roll  = new THREE.Matrix4().makeRotationX(degToRad(rollDeg));

  const unrealRotMatrix = new THREE.Matrix4()
    .multiply(yaw)
    .multiply(pitch)
    .multiply(roll);

  const quat = new THREE.Quaternion();
  unrealRotMatrix.decompose(new THREE.Vector3(), quat, new THREE.Vector3());
  quat.normalize();

  // Correction to match Unreal's printed quaternion values
  quat.set(-quat.x, -quat.y, quat.z, quat.w).normalize();
  return quat;
}

function unrealQuatToThreeQuat(unrealQuat: THREE.Quaternion): THREE.Quaternion {
  const unrealRotMatrix = new THREE.Matrix4().makeRotationFromQuaternion(unrealQuat);

  const threeRotMatrix = new THREE.Matrix4()
    .multiplyMatrices(BASIS_CHANGE, unrealRotMatrix)
    .multiply(BASIS_CHANGE_INV);

  const quat = new THREE.Quaternion();
  threeRotMatrix.decompose(new THREE.Vector3(), quat, new THREE.Vector3());
  return quat.normalize();
}

function createDrumMesh(inst: { name: string; class: string; location?: number[]; rotation?: number[]; scale?: number[] }): THREE.Group {
  const parent = new THREE.Group();
  parent.name = inst.name;

  const geometry = createGeometryForInstrument(inst.class);
  const material = createMaterialForInstrument(inst.class);
  const mesh = new THREE.Mesh(geometry, material);
  mesh.castShadow = true;
  mesh.receiveShadow = true;

  const unrealQuat = rotationArrayToUnrealQuat(inst.rotation ?? [0, 0, 0]);
  const threeQuat  = unrealQuatToThreeQuat(unrealQuat);

  parent.position.copy(unrealLocationToThree(inst.location ?? [0, 0, 0]));
  parent.quaternion.copy(threeQuat);
  parent.scale.copy(unrealScaleToThree(inst.scale));

  parent.add(mesh);
  return parent;
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
    scene.background = new THREE.Color(0x1e1e22);

    // Camera in meter-scale scene; orbit radius ~3m
    const camera = new THREE.OrthographicCamera(
      -width / height * 2, width / height * 2, 2, -2, 0.01, 100
    );
    camera.position.set(3, 2, 3);
    camera.lookAt(0, 0.5, 0);
    camera.zoom = 1.5;
    camera.updateProjectionMatrix();

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(window.devicePixelRatio);
    mount.appendChild(renderer.domElement);

    scene.add(new THREE.AmbientLight(0xffffff, 0.6));
    const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
    dirLight.position.set(2, 4, 2);
    scene.add(dirLight);

    // Ground plane
    const ground = new THREE.Mesh(
      new THREE.CylinderGeometry(2, 2, 0.05, 32),
      new THREE.MeshLambertMaterial({ color: 0x1e293b })
    );
    // ground.rotation.x = -Math.PI / 2;
    scene.add(ground);

    const orbitTarget = new THREE.Vector3(0, 0.5, 0);

    for (const inst of mappingStore.drumSet.instruments) {
      scene.add(createDrumMesh(inst));
      //keep track of the snare position for later to center orbit around it
      if (isSnareClass(inst.class) && inst.location) {
        const snarePos = unrealLocationToThree(inst.location);
        orbitTarget.copy(snarePos);
      }
    }

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.copy(orbitTarget);
    controls.autoRotate = true;
    controls.autoRotateSpeed = 1.0;
    // controls.enablePan = false;
    controls.update();

    let animFrameId: number;
    function animate() {
      animFrameId = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    }
    animate();

    return () => {
      cancelAnimationFrame(animFrameId);
      controls.dispose();
      mount.removeChild(renderer.domElement);
      renderer.dispose();
    };
  }, [mappingStore.drumSet]);

  if (!mappingStore.drumSet) return null;

  return (
    <Card className="mt-4">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
        <CardTitle>3D Drum Kit Preview</CardTitle>
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
