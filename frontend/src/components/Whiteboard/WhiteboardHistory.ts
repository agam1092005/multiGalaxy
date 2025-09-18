import { Canvas } from 'fabric';

export class WhiteboardHistory {
  private canvas: Canvas;
  private history: string[] = [];
  private currentIndex: number = -1;
  private maxHistorySize: number = 50;

  constructor(canvas: Canvas) {
    this.canvas = canvas;
    this.saveState(); // Save initial empty state
  }

  saveState(): void {
    // Remove any states after current index (when user made changes after undo)
    this.history = this.history.slice(0, this.currentIndex + 1);
    
    // Add new state
    const state = JSON.stringify(this.canvas.toJSON());
    this.history.push(state);
    this.currentIndex++;

    // Limit history size
    if (this.history.length > this.maxHistorySize) {
      this.history.shift();
      this.currentIndex--;
    }
  }

  undo(): boolean {
    if (!this.canUndo()) return false;

    this.currentIndex--;
    this.loadState(this.history[this.currentIndex]);
    return true;
  }

  redo(): boolean {
    if (!this.canRedo()) return false;

    this.currentIndex++;
    this.loadState(this.history[this.currentIndex]);
    return true;
  }

  canUndo(): boolean {
    return this.currentIndex > 0;
  }

  canRedo(): boolean {
    return this.currentIndex < this.history.length - 1;
  }

  private loadState(state: string): void {
    this.canvas.loadFromJSON(state, () => {
      this.canvas.renderAll();
    });
  }

  clear(): void {
    this.history = [];
    this.currentIndex = -1;
    this.saveState();
  }

  getHistorySize(): number {
    return this.history.length;
  }

  getCurrentIndex(): number {
    return this.currentIndex;
  }
}