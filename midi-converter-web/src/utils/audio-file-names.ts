/**
 * Resolves the file names written into the RLRR's audioFileData / coverImagePath
 * and used for the entries inside the exported ZIP. Both must agree, so they
 * share this one resolver.
 *
 * Matches the desktop converter (midiconvert.py), which stores the plain file
 * name of each track next to the .rlrr file.
 */

export interface AudioFileSet {
  songTracks: File[];
  drumTracks: File[];
  songPreview?: File | null;
  coverImage?: File | null;
}

export interface ResolvedAudioFileNames {
  songTracks: string[];
  drumTracks: string[];
  songPreview: string;
  coverImage: string;
}

/**
 * Strip any directory component - drag-and-dropped folders give us paths.
 */
function baseName(name: string): string {
  const parts = name.split(/[\\/]/);
  return parts[parts.length - 1] || name;
}

/**
 * Two tracks can share a name (e.g. both "drums.wav" from different folders).
 * They'd collapse into a single ZIP entry, so suffix the later ones.
 */
function makeUnique(name: string, used: Set<string>): string {
  const key = name.toLowerCase();
  if (!used.has(key)) {
    used.add(key);
    return name;
  }

  const lastDot = name.lastIndexOf('.');
  const stem = lastDot !== -1 ? name.substring(0, lastDot) : name;
  const ext = lastDot !== -1 ? name.substring(lastDot) : '';

  for (let i = 2; ; i++) {
    const candidate = `${stem}_${i}${ext}`;
    if (!used.has(candidate.toLowerCase())) {
      used.add(candidate.toLowerCase());
      return candidate;
    }
  }
}

export function resolveAudioFileNames(files: AudioFileSet): ResolvedAudioFileNames {
  const used = new Set<string>();

  return {
    songTracks: files.songTracks.map((f) => makeUnique(baseName(f.name), used)),
    drumTracks: files.drumTracks.map((f) => makeUnique(baseName(f.name), used)),
    songPreview: files.songPreview ? makeUnique(baseName(files.songPreview.name), used) : '',
    coverImage: files.coverImage ? makeUnique(baseName(files.coverImage.name), used) : '',
  };
}
