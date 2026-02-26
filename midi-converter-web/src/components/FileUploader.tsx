import { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { cn } from '@/lib/utils';

interface FileUploaderProps {
  label: string;
  accept: Record<string, string[]>;
  maxFiles?: number;
  onFilesSelected: (files: File[]) => void;
  currentFiles?: File[];
  onRemoveFile?: (index: number) => void;
  description?: string;
}

export function FileUploader({
  label,
  accept,
  maxFiles = 1,
  onFilesSelected,
  currentFiles = [],
  onRemoveFile,
  description,
}: FileUploaderProps) {
  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      onFilesSelected(acceptedFiles);
    },
    [onFilesSelected]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept,
    maxFiles,
    multiple: maxFiles > 1,
  });

  return (
    <div className="mb-6">
      {label && <Label>{label}</Label>}
      {description && <p className="text-sm text-muted-foreground mb-2">{description}</p>}

      <div
        {...getRootProps()}
        className={cn(
          'border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors',
          isDragActive
            ? 'border-primary bg-primary/10'
            : 'border-border bg-muted/50 hover:border-primary/50'
        )}
      >
        <input {...getInputProps()} />
        <p className="text-muted-foreground">
          {isDragActive
            ? 'Drop files here...'
            : maxFiles > 1
            ? `Drag & drop files here, or click to select (max ${maxFiles})`
            : 'Drag & drop a file here, or click to select'}
        </p>
      </div>

      {currentFiles.length > 0 && (
        <div className="mt-3 space-y-2">
          {currentFiles.map((file, index) => (
            <div key={index} className="flex justify-between items-center p-2 bg-secondary rounded">
              <span className="text-sm text-foreground">{file.name}</span>
              {onRemoveFile && (
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => onRemoveFile(index)}
                >
                  Remove
                </Button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
