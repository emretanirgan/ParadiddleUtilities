import JSZip from 'jszip';
import type { RLRROutput } from '../types/rlrr.types';
import { resolveAudioFileNames } from './audio-file-names';

/**
 * File handling utilities for reading and packaging files.
 */
export class FileHandler {
  /**
   * Read a file as ArrayBuffer.
   */
  static async readAsArrayBuffer(file: File): Promise<ArrayBuffer> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result as ArrayBuffer);
      reader.onerror = reject;
      reader.readAsArrayBuffer(file);
    });
  }

  /**
   * Read a file as text.
   */
  static async readAsText(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result as string);
      reader.onerror = reject;
      reader.readAsText(file);
    });
  }

  /**
   * Read a file as DataURL.
   */
  static async readAsDataURL(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result as string);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }

  /**
   * Create a ZIP package containing RLRR file and audio files.
   */
  static async createRLRRPackage(
    rlrrData: RLRROutput,
    songName: string,
    difficulty: string,
    audioFiles: {
      songTracks: File[];
      drumTracks: File[];
      songPreview?: File;
      coverImage?: File;
    }
  ): Promise<Blob> {
    const zip = new JSZip();

    // Create folder for this song
    const songFolder = zip.folder(songName);
    if (!songFolder) {
      throw new Error('Failed to create song folder in ZIP');
    }

    // Add RLRR JSON file
    const rlrrFileName = `${songName}_${difficulty}.rlrr`;
    const rlrrContent = JSON.stringify(rlrrData, null, 2);
    songFolder.file(rlrrFileName, rlrrContent);

    // Add audio files under the same names the RLRR references
    const fileNames = resolveAudioFileNames(audioFiles);

    // Song tracks
    for (let i = 0; i < audioFiles.songTracks.length; i++) {
      const buffer = await this.readAsArrayBuffer(audioFiles.songTracks[i]);
      songFolder.file(fileNames.songTracks[i], buffer);
    }

    // Drum tracks
    for (let i = 0; i < audioFiles.drumTracks.length; i++) {
      const buffer = await this.readAsArrayBuffer(audioFiles.drumTracks[i]);
      songFolder.file(fileNames.drumTracks[i], buffer);
    }

    // Song preview
    if (audioFiles.songPreview) {
      const buffer = await this.readAsArrayBuffer(audioFiles.songPreview);
      songFolder.file(fileNames.songPreview, buffer);
    }

    // Cover image
    if (audioFiles.coverImage) {
      const buffer = await this.readAsArrayBuffer(audioFiles.coverImage);
      songFolder.file(fileNames.coverImage, buffer);
    }

    // Generate ZIP
    return zip.generateAsync({ type: 'blob' });
  }

  /**
   * Download a blob as a file.
   */
  static downloadBlob(blob: Blob, filename: string): void {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  /**
   * Download JSON data as a file.
   */
  static downloadJSON(data: any, filename: string): void {
    const json = JSON.stringify(data, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    this.downloadBlob(blob, filename);
  }
}
