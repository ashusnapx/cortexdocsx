"use client";

import { useState, useRef } from "react";
import {
  UploadCloud,
  FileText,
  AlertCircle,
  CheckCircle2,
  Loader2,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useUploadDocument, useDocuments } from "../hooks/useDashboard";
import { Card } from "@/shared/ui/card";
import { Badge } from "@/shared/ui/badge";

export function DocumentUploader() {
  const [isDragging, setIsDragging] = useState(false);
  const { mutate: uploadDocument, isPending } = useUploadDocument();
  const { data: docsResponse } = useDocuments();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const documents = docsResponse?.data?.documents || [];

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      if (file.type === "application/pdf") {
        uploadDocument(file);
      }
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      uploadDocument(e.target.files[0]);
    }
    // reset input so the same file can be uploaded again if needed
    e.target.value = "";
  };

  return (
    <div className='flex flex-col gap-6'>
      {/* Upload Zone */}
      <Card
        className={`relative overflow-hidden transition-all duration-300 ${
          isDragging ?
            "border-primary bg-primary/5 shadow-md"
          : "border-dashed hover:border-muted-foreground/50"
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <div className='flex flex-col items-center justify-center px-6 py-16 text-center'>
          <input
            type='file'
            accept='.pdf'
            className='hidden'
            ref={fileInputRef}
            onChange={handleFileChange}
            disabled={isPending}
          />

          <AnimatePresence mode='wait'>
            {isPending ?
              <motion.div
                key='uploading'
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className='flex flex-col items-center gap-4'
              >
                <Loader2 className='h-10 w-10 animate-spin text-primary' />
                <div className='space-y-1'>
                  <p className='text-sm font-medium text-foreground'>
                    Processing Document...
                  </p>
                  <p className='text-xs text-muted-foreground'>
                    Chunking, embedding, and indexing in background.
                  </p>
                </div>
              </motion.div>
            : <motion.div
                key='idle'
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className='flex flex-col items-center gap-4 cursor-pointer'
                onClick={() => fileInputRef.current?.click()}
              >
                <div className='flex h-16 w-16 items-center justify-center rounded-2xl bg-surface transition-transform hover:scale-105'>
                  <UploadCloud className='h-8 w-8 text-muted-foreground' />
                </div>
                <div className='space-y-1'>
                  <p className='text-base font-medium text-foreground'>
                    Click to upload or drag and drop
                  </p>
                  <p className='text-sm text-muted-foreground'>
                    PDF files only (max 50MB)
                  </p>
                </div>
              </motion.div>
            }
          </AnimatePresence>
        </div>
      </Card>

      {/* Indexed Documents List */}
      {documents.length > 0 && (
        <div className='flex flex-col gap-3'>
          <h3 className='text-sm font-semibold text-foreground'>
            Indexed Documents ({documents.length})
          </h3>
          <div className='grid gap-2'>
            {documents.map((doc) => (
              <Card
                key={doc.id}
                className='p-4 transition-colors hover:bg-surface'
              >
                <div className='flex items-center justify-between'>
                  <div className='flex items-center gap-3'>
                    <FileText className='h-5 w-5 text-muted-foreground' />
                    <div>
                      <p className='text-sm font-medium text-foreground'>
                        {doc.original_filename}
                      </p>
                      <p className='text-xs text-muted-foreground'>
                        {doc.page_count ?
                          `${doc.page_count} pages`
                        : "Pending pages"}{" "}
                        •{" "}
                        {doc.chunk_count ?
                          `${doc.chunk_count} chunks`
                        : "Pending chunks"}
                      </p>
                    </div>
                  </div>
                  <div>
                    {doc.status === "COMPLETED" && (
                      <Badge variant='success' className='gap-1'>
                        <CheckCircle2 className='h-3 w-3' /> Ready
                      </Badge>
                    )}
                    {doc.status === "FAILED" && (
                      <Badge variant='error' className='gap-1'>
                        <AlertCircle className='h-3 w-3' /> Failed
                      </Badge>
                    )}
                    {(doc.status === "PENDING" ||
                      doc.status === "PROCESSING") && (
                      <Badge
                        variant='secondary'
                        className='gap-1 bg-blue-50 text-blue-700'
                      >
                        <Loader2 className='h-3 w-3 animate-spin' /> Processing
                      </Badge>
                    )}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
