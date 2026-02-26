import { useMappingStore } from '../stores/mapping-store';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';

const difficulties = ['easy', 'medium', 'hard', 'expert'] as const;

export function DifficultySelector() {
  const { difficulty, setDifficulty } = useMappingStore();

  return (
    <div className="mb-6">
      <Label>Difficulty Level</Label>
      <div className="flex gap-2 mt-2">
        {difficulties.map((diff) => (
          <Button
            key={diff}
            variant={difficulty === diff ? 'default' : 'outline'}
            className="flex-1 capitalize"
            onClick={() => setDifficulty(diff)}
          >
            {diff}
          </Button>
        ))}
      </div>
    </div>
  );
}
