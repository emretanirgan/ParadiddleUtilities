import { useState } from 'react';
import { useMappingStore } from '../stores/mapping-store';
import type { MidiMapping } from '../types/mapping.types';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

interface MappingEditorProps {
  onClose: () => void;
}

export function MappingEditor({ onClose }: MappingEditorProps) {
  const mappingStore = useMappingStore();
  const [editedMapping, setEditedMapping] = useState<MidiMapping | null>(
    mappingStore.mapping ? JSON.parse(JSON.stringify(mappingStore.mapping)) : null
  );
  const [newNoteInputs, setNewNoteInputs] = useState<Record<string, string>>({});

  if (!editedMapping) {
    return (
      <Card className="mt-4">
        <CardContent className="pt-6">
          <p className="text-muted-foreground">No mapping loaded</p>
        </CardContent>
      </Card>
    );
  }

  const currentDifficulty = mappingStore.difficulty;
  const drumMapping = editedMapping[currentDifficulty];

  const handleAddNote = (drumName: string) => {
    const inputValue = newNoteInputs[drumName];
    if (!inputValue) return;

    const noteNumber = parseInt(inputValue, 10);
    if (isNaN(noteNumber) || noteNumber < 0 || noteNumber > 127) {
      alert('Please enter a valid MIDI note (0-127)');
      return;
    }

    const drumData = drumMapping[drumName];
    if (Array.isArray(drumData)) {
      if (!drumData.includes(noteNumber)) {
        setEditedMapping({
          ...editedMapping,
          [currentDifficulty]: {
            ...drumMapping,
            [drumName]: [...drumData, noteNumber],
          },
        });
      }
    } else if (drumData && typeof drumData === 'object' && 'notes' in drumData) {
      if (!drumData.notes.includes(noteNumber)) {
        setEditedMapping({
          ...editedMapping,
          [currentDifficulty]: {
            ...drumMapping,
            [drumName]: {
              ...drumData,
              notes: [...drumData.notes, noteNumber],
            },
          },
        });
      }
    }

    setNewNoteInputs({ ...newNoteInputs, [drumName]: '' });
  };

  const handleRemoveNote = (drumName: string, noteToRemove: number) => {
    const drumData = drumMapping[drumName];
    if (Array.isArray(drumData)) {
      setEditedMapping({
        ...editedMapping,
        [currentDifficulty]: {
          ...drumMapping,
          [drumName]: drumData.filter((n) => n !== noteToRemove),
        },
      });
    } else if (drumData && typeof drumData === 'object' && 'notes' in drumData) {
      setEditedMapping({
        ...editedMapping,
        [currentDifficulty]: {
          ...drumMapping,
          [drumName]: {
            ...drumData,
            notes: drumData.notes.filter((n) => n !== noteToRemove),
          },
        },
      });
    }
  };

  const handleUpdateToggleNote = (drumName: string, toggleNote: string) => {
    const drumData = drumMapping[drumName];
    if (drumData && typeof drumData === 'object' && 'notes' in drumData) {
      const toggleValue = toggleNote === '' ? undefined : parseInt(toggleNote, 10);
      if (toggleNote !== '' && (isNaN(toggleValue!) || toggleValue! < 0 || toggleValue! > 127)) {
        return;
      }

      setEditedMapping({
        ...editedMapping,
        [currentDifficulty]: {
          ...drumMapping,
          [drumName]: {
            ...drumData,
            toggle_note: toggleValue,
          },
        },
      });
    }
  };

  const handleSave = () => {
    mappingStore.updateMapping(editedMapping);
    onClose();
  };

  const getNotes = (drumData: any): number[] => {
    if (Array.isArray(drumData)) {
      return drumData;
    } else if (drumData && typeof drumData === 'object' && 'notes' in drumData) {
      return drumData.notes;
    }
    return [];
  };

  const getToggleNote = (drumData: any): number | undefined => {
    if (drumData && typeof drumData === 'object' && 'toggle_note' in drumData) {
      return drumData.toggle_note;
    }
    return undefined;
  };

  return (
    <Card className="mt-4">
      <CardHeader className="pb-4">
        <div className="flex justify-between items-center">
          <CardTitle className="text-lg">Edit Mapping - {currentDifficulty.toUpperCase()}</CardTitle>
          <div className="flex gap-2">
            <Button size="sm" onClick={handleSave}>Save</Button>
            <Button size="sm" variant="outline" onClick={onClose}>Cancel</Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Drum</TableHead>
                <TableHead>MIDI Notes</TableHead>
                <TableHead>Toggle Note</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {Object.keys(drumMapping).map((drumName) => {
                const drumData = drumMapping[drumName];
                const notes = getNotes(drumData);
                const toggleNote = getToggleNote(drumData);

                return (
                  <TableRow key={drumName}>
                    <TableCell className="font-semibold">{drumName}</TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1 items-center">
                        {notes.map((note) => (
                          <Badge key={note} variant="secondary" className="gap-1">
                            {note}
                            <button
                              onClick={() => handleRemoveNote(drumName, note)}
                              className="text-destructive hover:text-destructive/80 font-bold ml-1"
                            >
                              x
                            </button>
                          </Badge>
                        ))}
                        <Input
                          type="number"
                          min={0}
                          max={127}
                          placeholder="Note"
                          value={newNoteInputs[drumName] || ''}
                          onChange={(e) =>
                            setNewNoteInputs({ ...newNoteInputs, [drumName]: e.target.value })
                          }
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') {
                              handleAddNote(drumName);
                            }
                          }}
                          className="w-16 h-7 text-xs"
                        />
                        <Button size="sm" className="h-7 text-xs" onClick={() => handleAddNote(drumName)}>
                          + Add
                        </Button>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Input
                        type="number"
                        min={0}
                        max={127}
                        placeholder="None"
                        value={toggleNote ?? ''}
                        onChange={(e) => handleUpdateToggleNote(drumName, e.target.value)}
                        className="w-20 h-7 text-xs"
                      />
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>

        <p className="mt-4 text-xs text-muted-foreground">
          MIDI notes: 0-127. Toggle notes are used for hi-hat pedal control (Rock Band format).
        </p>
      </CardContent>
    </Card>
  );
}
