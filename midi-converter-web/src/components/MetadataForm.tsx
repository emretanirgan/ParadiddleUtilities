import { useConversionStore } from '../stores/conversion-store';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';

export function MetadataForm() {
  const { metadata, updateMetadata } = useConversionStore();

  return (
    <div className="mb-6">
      <h3 className="text-lg font-bold mb-4 text-foreground">Song Metadata</h3>

      <div className="mb-4">
        <Label htmlFor="title">
          Song Title <span className="text-destructive">*</span>
        </Label>
        <Input
          id="title"
          type="text"
          value={metadata.title}
          onChange={(e) => updateMetadata({ title: e.target.value })}
          placeholder="Enter song title"
          className="mt-1"
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="mb-4">
          <Label htmlFor="artist">Artist</Label>
          <Input
            id="artist"
            type="text"
            value={metadata.artist}
            onChange={(e) => updateMetadata({ artist: e.target.value })}
            placeholder="Artist name"
            className="mt-1"
          />
        </div>

        <div className="mb-4">
          <Label htmlFor="creator">Creator</Label>
          <Input
            id="creator"
            type="text"
            value={metadata.creator}
            onChange={(e) => updateMetadata({ creator: e.target.value })}
            placeholder="Your name"
            className="mt-1"
          />
        </div>
      </div>

      <div className="mb-4">
        <Label htmlFor="description">Description</Label>
        <Textarea
          id="description"
          value={metadata.description}
          onChange={(e) => updateMetadata({ description: e.target.value })}
          placeholder="Song description (optional)"
          className="mt-1 min-h-[80px]"
        />
      </div>

      <div className="mb-4">
        <Label htmlFor="complexity">Complexity (1-5)</Label>
        <Input
          id="complexity"
          type="number"
          min={1}
          max={5}
          value={metadata.complexity}
          onChange={(e) => updateMetadata({ complexity: parseInt(e.target.value) || 1 })}
          className="mt-1"
        />
      </div>
    </div>
  );
}
