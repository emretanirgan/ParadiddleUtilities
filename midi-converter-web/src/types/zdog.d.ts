declare module 'zdog' {
  export interface IllustrationOptions {
    element: HTMLCanvasElement;
    dragRotate?: boolean;
    resize?: boolean;
    rotate?: { x?: number; y?: number; z?: number };
  }

  export class Illustration {
    constructor(options: IllustrationOptions);
    rotate: { x: number; y: number; z: number };
    updateRenderGraph(): void;
  }

  export interface GroupOptions {
    addTo: Illustration | Group;
    translate?: { x?: number; y?: number; z?: number };
    rotate?: { x?: number; y?: number; z?: number };
  }

  export class Group {
    constructor(options: GroupOptions);
  }

  export interface CylinderOptions {
    addTo: Group;
    diameter: number;
    length: number;
    stroke?: boolean;
    color?: string;
    backface?: string;
  }

  export class Cylinder {
    constructor(options: CylinderOptions);
  }
}
