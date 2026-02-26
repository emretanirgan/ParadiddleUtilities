/**
 * Handles mouse interactions for zoom and pan on the visualization canvas.
 * - Mouse wheel: Zoom in/out
 * - Click: Seek to time
 * - Drag: Pan timeline
 */

export interface ZoomPanCallbacks {
  onZoomChange: (zoom: number) => void;
  onScrollChange: (offset: number) => void;
  onSeek: (time: number) => void;
}

export class ZoomPanController {
  private canvas: HTMLCanvasElement;
  private callbacks: ZoomPanCallbacks;
  private isDragging = false;
  private lastMouseX = 0;
  private zoom = 1.0;
  private scrollOffset = 0;

  constructor(canvas: HTMLCanvasElement, callbacks: ZoomPanCallbacks) {
    this.canvas = canvas;
    this.callbacks = callbacks;

    this.attachEventListeners();
  }

  /**
   * Update zoom level (called from external state changes)
   */
  setZoom(zoom: number): void {
    this.zoom = zoom;
  }

  /**
   * Update scroll offset (called from external state changes)
   */
  setScrollOffset(offset: number): void {
    this.scrollOffset = offset;
  }

  /**
   * Attach mouse event listeners
   */
  private attachEventListeners(): void {
    // Mouse wheel for zoom
    this.canvas.addEventListener('wheel', this.handleWheel);

    // Mouse down to start drag or seek
    this.canvas.addEventListener('mousedown', this.handleMouseDown);

    // Mouse move for dragging
    this.canvas.addEventListener('mousemove', this.handleMouseMove);

    // Mouse up to end drag
    this.canvas.addEventListener('mouseup', this.handleMouseUp);
    this.canvas.addEventListener('mouseleave', this.handleMouseUp);
  }

  /**
   * Detach event listeners (for cleanup)
   */
  detach(): void {
    this.canvas.removeEventListener('wheel', this.handleWheel);
    this.canvas.removeEventListener('mousedown', this.handleMouseDown);
    this.canvas.removeEventListener('mousemove', this.handleMouseMove);
    this.canvas.removeEventListener('mouseup', this.handleMouseUp);
    this.canvas.removeEventListener('mouseleave', this.handleMouseUp);
  }

  /**
   * Handle mouse wheel for zoom
   */
  private handleWheel = (e: WheelEvent): void => {
    e.preventDefault();

    const zoomSpeed = 0.001;
    const delta = -e.deltaY * zoomSpeed;
    const newZoom = Math.max(0.1, Math.min(10, this.zoom + delta));

    // Zoom towards mouse position
    const rect = this.canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseRatio = (mouseX + this.scrollOffset) / (this.canvas.width * this.zoom);

    // Adjust scroll offset to keep mouse position fixed during zoom
    const newScrollOffset = mouseRatio * this.canvas.width * newZoom - mouseX;

    this.zoom = newZoom;
    this.scrollOffset = Math.max(0, newScrollOffset);

    this.callbacks.onZoomChange(newZoom);
    this.callbacks.onScrollChange(this.scrollOffset);
  };

  /**
   * Handle mouse down (start drag or seek)
   */
  private handleMouseDown = (e: MouseEvent): void => {
    const rect = this.canvas.getBoundingClientRect();
    this.lastMouseX = e.clientX - rect.left;

    if (e.button === 0) {
      // Left click
      if (e.shiftKey) {
        // Shift+click to seek
        this.handleSeek(this.lastMouseX);
      } else {
        // Start drag
        this.isDragging = true;
        this.canvas.style.cursor = 'grabbing';
      }
    }
  };

  /**
   * Handle mouse move (drag)
   */
  private handleMouseMove = (e: MouseEvent): void => {
    if (!this.isDragging) {
      return;
    }

    const rect = this.canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const deltaX = this.lastMouseX - mouseX;

    this.scrollOffset = Math.max(0, this.scrollOffset + deltaX);
    this.lastMouseX = mouseX;

    this.callbacks.onScrollChange(this.scrollOffset);
  };

  /**
   * Handle mouse up (end drag)
   */
  private handleMouseUp = (): void => {
    if (this.isDragging) {
      this.isDragging = false;
      this.canvas.style.cursor = 'default';
    }
  };

  /**
   * Handle seek (convert x position to time)
   */
  private handleSeek(x: number): void {
    // This calculation should match timeFromX in PianoRollRenderer
    // For now, we'll pass the x coordinate and let the component handle conversion
    this.callbacks.onSeek(x);
  }
}
