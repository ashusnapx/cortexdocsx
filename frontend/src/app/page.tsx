"use client";

import { motion, AnimatePresence } from "framer-motion";
import {
  Upload,
  Search,
  Shield,
  ChevronRight,
  ArrowRight,
  Layers,
  Eye,
  Zap,
  GitBranch,
  BarChart3,
  Lock,
} from "lucide-react";
import Link from "next/link";
import { useState, useCallback, useRef, useEffect } from "react";
import type {
  ChunkScore,
  ConfidenceBreakdown,
  Contradiction,
  Citation,
  DocumentResponse,
  QueryResponse,
  UploadResponse,
} from "@/lib/types";
import { PIPELINE_STAGES, INGESTION_STAGES } from "@/lib/types";
import { uploadDocument, listDocuments, executeQuery } from "@/lib/api";

/* ═══════════════════════════════════════════════════
   SECTION BADGE (pill label like ChronoTask)
   ═══════════════════════════════════════════════════ */
function SectionBadge({ children }: { children: React.ReactNode }) {
  return (
    <span className='inline-block text-[12px] font-medium text-gray-500 border border-gray-200 rounded-full px-4 py-1.5 mb-5'>
      {children}
    </span>
  );
}

/* ═══════════════════════════════════════════════════
   FEATURE CARD
   ═══════════════════════════════════════════════════ */
function FeatureCard({
  icon: Icon,
  title,
  description,
}: {
  icon: React.ElementType;
  title: string;
  description: string;
}) {
  return (
    <div className='text-center p-8'>
      <div className='w-12 h-12 rounded-2xl bg-gray-100 flex items-center justify-center mx-auto mb-4'>
        <Icon className='w-5 h-5 text-gray-600' />
      </div>
      <h4 className='text-[15px] font-semibold text-gray-900 mb-2'>{title}</h4>
      <p className='text-[13px] text-gray-500 leading-relaxed'>{description}</p>
    </div>
  );
}

/* ═══════════════════════════════════════════════════
   MAIN PAGE
   ═══════════════════════════════════════════════════ */
export default function Home() {
  const [activeTab, setActiveTab] = useState<"upload" | "query">("upload");
  const [query, setQuery] = useState("");
  const [querying, setQuerying] = useState(false);
  const [queryResponse, setQueryResponse] = useState<QueryResponse | null>(
    null,
  );
  const [streamedAnswer, setStreamedAnswer] = useState("");
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [alpha, setAlpha] = useState(0.7);
  const [beta, setBeta] = useState(0.3);
  const [reranking, setReranking] = useState(true);
  const [hybrid, setHybrid] = useState(true);

  const loadDocuments = useCallback(async () => {
    try {
      const response = await listDocuments();
      if (response.success && response.data)
        setDocuments(response.data.documents);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  const handleQuery = useCallback(async () => {
    if (!query.trim()) return;
    setQuerying(true);
    setError(null);
    setQueryResponse(null);
    setStreamedAnswer("");
    try {
      const response = await executeQuery({
        query: query.trim(),
        alpha,
        beta,
        enable_reranking: reranking,
        enable_hybrid: hybrid,
      });
      if (response.success && response.data) {
        setQueryResponse(response.data);
        setStreamedAnswer(response.data.response_text);
      } else setError(response.error?.message || "Query failed");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Query failed");
    } finally {
      setQuerying(false);
    }
  }, [query, alpha, beta, reranking, hybrid]);

  const scrollToDash = () =>
    document
      .getElementById("dashboard")
      ?.scrollIntoView({ behavior: "smooth" });

  return (
    <div className='min-h-screen bg-white text-gray-900'>
      {/* ═══════ HERO ═══════ */}
      <section className='pt-28 pb-20 md:pt-40 md:pb-32 text-center px-6'>
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.9, ease: [0.25, 0.1, 0.25, 1] }}
          className='max-w-[720px] mx-auto'
        >
          {/* Logo icon */}
          <div className='w-14 h-14 rounded-2xl bg-black flex items-center justify-center mx-auto mb-8 shadow-lg'>
            <Zap className='w-6 h-6 text-white' />
          </div>

          <h1 className='text-[40px] md:text-[64px] font-bold leading-[1.08] tracking-tight text-gray-900 mb-2'>
            Ingest, query, and verify
          </h1>
          <h1 className='text-[40px] md:text-[64px] font-bold leading-[1.08] tracking-tight text-gray-400 mb-8'>
            all in one place
          </h1>

          <p className='text-[17px] text-gray-500 leading-relaxed max-w-[480px] mx-auto mb-10'>
            A production-grade RAG engine with full pipeline transparency. Every
            embedding, rescore, and contradiction — observable in real-time.
          </p>

          <div className='flex items-center justify-center gap-4 flex-wrap'>
            <button
              onClick={() => {
                setActiveTab("upload");
                scrollToDash();
              }}
              className='inline-flex items-center gap-2 px-8 py-3.5 bg-blue-500 text-white text-[15px] font-medium rounded-full border-none cursor-pointer hover:bg-blue-600 transition-colors duration-200'
            >
              Get free demo
            </button>
            <Link
              href='/system-design'
              className='inline-flex items-center gap-2 px-8 py-3.5 text-[15px] font-medium text-gray-500 rounded-full border border-gray-200 no-underline hover:border-gray-400 hover:text-gray-900 transition-all duration-200'
            >
              View Architecture <ArrowRight className='w-4 h-4' />
            </Link>
          </div>
        </motion.div>
      </section>

      {/* ═══════ SOLUTIONS ═══════ */}
      <section id='solutions' className='py-20 md:py-28 px-6 bg-white'>
        <div className='max-w-[1000px] mx-auto text-center'>
          <SectionBadge>Solutions</SectionBadge>
          <h2 className='text-[32px] md:text-[44px] font-bold tracking-tight leading-[1.1] text-gray-900 mb-4'>
            Solve your document
            <br />
            intelligence challenges
          </h2>
          <p className='text-[16px] text-gray-500 mb-16 max-w-[500px] mx-auto'>
            From ingestion to answer generation — every step is transparent and
            auditable.
          </p>

          <div className='grid grid-cols-1 md:grid-cols-3 gap-0 divide-y md:divide-y-0 md:divide-x divide-gray-100'>
            <FeatureCard
              icon={Layers}
              title='Hybrid Retrieval'
              description='Combines dense vector search (FAISS) with sparse keyword search (BM25) for superior recall on every query.'
            />
            <FeatureCard
              icon={Eye}
              title='Full Observability'
              description='Every pipeline stage is timed. Query logs store all intermediate results for replay and debugging.'
            />
            <FeatureCard
              icon={Shield}
              title='Contradiction Detection'
              description='Automatically surfaces conflicting claims across documents. Know when your sources disagree.'
            />
          </div>
        </div>
      </section>

      {/* ═══════ FEATURES ═══════ */}
      <section id='features' className='py-20 md:py-28 px-6 bg-[#f7f7f8]'>
        <div className='max-w-[1000px] mx-auto text-center'>
          <SectionBadge>Features</SectionBadge>
          <h2 className='text-[32px] md:text-[44px] font-bold tracking-tight leading-[1.1] text-gray-900 mb-4'>
            Keep everything in one place
          </h2>
          <p className='text-[16px] text-gray-500 mb-16'>
            Forget fragmented document pipelines.
          </p>

          {/* Feature Cards Grid */}
          <div className='grid grid-cols-1 md:grid-cols-2 gap-4'>
            {/* Card 1 — Ingestion */}
            <div className='bg-white rounded-3xl p-8 text-left border border-gray-100 hover:shadow-lg transition-shadow duration-300'>
              <div className='w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center mb-5'>
                <Upload className='w-5 h-5 text-blue-500' />
              </div>
              <h3 className='text-[18px] font-semibold text-gray-900 mb-2'>
                Smart Ingestion
              </h3>
              <p className='text-[14px] text-gray-500 leading-relaxed'>
                Upload PDFs and watch them get parsed, chunked, embedded, and
                indexed — with every stage timed and observable.
              </p>
            </div>

            {/* Card 2 — Retrieval */}
            <div className='bg-white rounded-3xl p-8 text-left border border-gray-100 hover:shadow-lg transition-shadow duration-300'>
              <div className='w-10 h-10 rounded-xl bg-green-50 flex items-center justify-center mb-5'>
                <Search className='w-5 h-5 text-green-600' />
              </div>
              <h3 className='text-[18px] font-semibold text-gray-900 mb-2'>
                Neural Retrieval
              </h3>
              <p className='text-[14px] text-gray-500 leading-relaxed'>
                Hybrid vector + BM25 search with cross-encoder reranking.
                Tunable alpha/beta parameters for precision control.
              </p>
            </div>

            {/* Card 3 — Confidence */}
            <div className='bg-white rounded-3xl p-8 text-left border border-gray-100 hover:shadow-lg transition-shadow duration-300'>
              <div className='w-10 h-10 rounded-xl bg-purple-50 flex items-center justify-center mb-5'>
                <BarChart3 className='w-5 h-5 text-purple-600' />
              </div>
              <h3 className='text-[18px] font-semibold text-gray-900 mb-2'>
                Confidence Scoring
              </h3>
              <p className='text-[14px] text-gray-500 leading-relaxed'>
                Four-factor confidence breakdown: similarity, reranker
                agreement, source agreement, and dispersion analysis.
              </p>
            </div>

            {/* Card 4 — Audit */}
            <div className='bg-white rounded-3xl p-8 text-left border border-gray-100 hover:shadow-lg transition-shadow duration-300'>
              <div className='w-10 h-10 rounded-xl bg-orange-50 flex items-center justify-center mb-5'>
                <GitBranch className='w-5 h-5 text-orange-600' />
              </div>
              <h3 className='text-[18px] font-semibold text-gray-900 mb-2'>
                Audit Logging
              </h3>
              <p className='text-[14px] text-gray-500 leading-relaxed'>
                Every query is deterministically replayable. Full telemetry —
                retrieval scores, reranking positions, confidence components.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════ ARCHITECTURE CTA ═══════ */}
      <section className='py-20 md:py-28 px-6 bg-white'>
        <div className='max-w-[800px] mx-auto text-center'>
          <SectionBadge>Architecture</SectionBadge>
          <h2 className='text-[32px] md:text-[44px] font-bold tracking-tight leading-[1.1] text-gray-900 mb-4'>
            Built for engineers
          </h2>
          <p className='text-[16px] text-gray-500 mb-10 max-w-[480px] mx-auto'>
            Explore the complete system design — HLD, LLD, data flows, ER
            diagrams, and every architectural decision documented.
          </p>
          <Link
            href='/system-design'
            className='inline-flex items-center gap-2 px-8 py-3.5 bg-gray-900 text-white text-[15px] font-medium rounded-full no-underline hover:bg-gray-800 transition-colors duration-200'
          >
            View System Design <ArrowRight className='w-4 h-4' />
          </Link>
        </div>
      </section>

      {/* ═══════ DASHBOARD ═══════ */}
      <section id='dashboard' className='py-20 md:py-28 px-6 bg-[#f7f7f8]'>
        <div className='max-w-[1000px] mx-auto'>
          <div className='text-center mb-14'>
            <SectionBadge>Dashboard</SectionBadge>
            <h2 className='text-[32px] md:text-[44px] font-bold tracking-tight leading-[1.1] text-gray-900 mb-4'>
              Try it yourself
            </h2>
            <p className='text-[16px] text-gray-500'>
              Ingest documents or search your knowledge base.
            </p>
          </div>

          {/* Tab Pills */}
          <div className='flex justify-center mb-10'>
            <div className='inline-flex bg-white rounded-full p-1 border border-gray-200 shadow-sm'>
              <TabPill
                active={activeTab === "upload"}
                onClick={() => setActiveTab("upload")}
              >
                <Upload className='w-3.5 h-3.5' /> Ingestion
              </TabPill>
              <TabPill
                active={activeTab === "query"}
                onClick={() => setActiveTab("query")}
              >
                <Search className='w-3.5 h-3.5' /> Retrieval
              </TabPill>
            </div>
          </div>

          {/* Content */}
          <AnimatePresence mode='wait'>
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.4, ease: [0.25, 0.1, 0.25, 1] }}
            >
              {activeTab === "upload" ?
                <UploadView
                  documents={documents}
                  onUploadComplete={loadDocuments}
                />
              : <QueryView
                  query={query}
                  setQuery={setQuery}
                  querying={querying}
                  error={error}
                  queryResponse={queryResponse}
                  streamedAnswer={streamedAnswer}
                  handleQuery={handleQuery}
                  alpha={alpha}
                  setAlpha={setAlpha}
                  beta={beta}
                  setBeta={setBeta}
                  reranking={reranking}
                  setReranking={setReranking}
                  hybrid={hybrid}
                  setHybrid={setHybrid}
                />
              }
            </motion.div>
          </AnimatePresence>
        </div>
      </section>
    </div>
  );
}

/* ═══════════════════════════════════════════════════
   TAB PILL
   ═══════════════════════════════════════════════════ */
function TabPill({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 px-5 py-2.5 rounded-full text-[13px] font-medium border-none cursor-pointer transition-all duration-200 ${
        active ?
          "bg-gray-900 text-white shadow-sm"
        : "bg-transparent text-gray-500 hover:text-gray-900"
      }`}
    >
      {children}
    </button>
  );
}

/* ═══════════════════════════════════════════════════
   UPLOAD VIEW
   ═══════════════════════════════════════════════════ */
function UploadView({
  documents,
  onUploadComplete,
}: {
  documents: DocumentResponse[];
  onUploadComplete: () => void;
}) {
  return (
    <div className='max-w-[640px] mx-auto'>
      <UploadPanel onUploadComplete={onUploadComplete} />

      {documents.length > 0 && (
        <div className='mt-12'>
          <p className='text-[12px] font-semibold uppercase tracking-wider text-gray-400 mb-4'>
            Indexed Documents · {documents.length}
          </p>
          <div className='flex flex-col gap-1.5'>
            {documents.map((doc) => (
              <div
                key={doc.id}
                className='flex items-center justify-between p-4 rounded-2xl bg-white border border-gray-100 hover:shadow-md transition-shadow duration-200 cursor-pointer'
              >
                <div className='flex items-center gap-3'>
                  <div className='w-9 h-9 rounded-xl bg-gray-100 flex items-center justify-center'>
                    <Search className='w-4 h-4 text-gray-400' />
                  </div>
                  <div>
                    <p className='text-[14px] font-medium text-gray-900'>
                      {doc.original_filename}
                    </p>
                    <p className='text-[12px] text-gray-400'>
                      {doc.page_count} pages · {doc.chunk_count} chunks
                    </p>
                  </div>
                </div>
                <ChevronRight className='w-4 h-4 text-gray-300' />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ─── Upload Panel ───────────────────────────────── */
function UploadPanel({ onUploadComplete }: { onUploadComplete: () => void }) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<UploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleUpload = useCallback(
    async (file: File) => {
      setUploading(true);
      setError(null);
      setUploadResult(null);
      try {
        const response = await uploadDocument(file);
        if (response.success && response.data) {
          setUploadResult(response.data);
          onUploadComplete();
        } else setError(response.error?.message || "Upload failed");
      } catch (err) {
        setError(err instanceof Error ? err.message : "Upload failed");
      } finally {
        setUploading(false);
      }
    },
    [onUploadComplete],
  );

  return (
    <div>
      <div
        onClick={() => fileInputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragging(false);
          const f = e.dataTransfer.files[0];
          if (f) handleUpload(f);
        }}
        className={`rounded-3xl border-2 border-dashed py-20 px-10 text-center cursor-pointer transition-all duration-300 ${
          isDragging ?
            "border-blue-400 bg-blue-50/50"
          : "border-gray-200 bg-white hover:border-gray-300"
        }`}
      >
        <input
          ref={fileInputRef}
          type='file'
          accept='.pdf'
          className='hidden'
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) handleUpload(f);
          }}
        />

        {uploading ?
          <div className='flex flex-col items-center gap-3'>
            <div className='w-8 h-8 border-2 border-gray-200 border-t-blue-500 rounded-full animate-spin' />
            <p className='text-[14px] text-gray-400'>Processing…</p>
          </div>
        : <>
            <div className='w-14 h-14 rounded-2xl bg-gray-100 flex items-center justify-center mx-auto mb-5'>
              <Upload className='w-6 h-6 text-gray-400' />
            </div>
            <p className='text-[17px] font-semibold text-gray-900 mb-1'>
              Drop a PDF here
            </p>
            <p className='text-[14px] text-gray-400'>
              or click to browse · max 50 MB
            </p>
          </>
        }
      </div>

      {error && (
        <div className='mt-4 p-4 rounded-2xl bg-red-50 border border-red-100 text-red-600 text-[14px] flex items-center gap-2.5'>
          <Shield className='w-4 h-4 shrink-0' /> {error}
        </div>
      )}

      {uploadResult?.timing && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className='mt-8 rounded-3xl bg-white border border-gray-100 p-8 shadow-sm'
        >
          <p className='text-[12px] font-semibold uppercase tracking-wider text-gray-400 mb-5'>
            Pipeline Results
          </p>
          {uploadResult.timing.stages.map((stage, i) => (
            <div
              key={i}
              className='flex justify-between items-center py-3 px-4 rounded-xl hover:bg-gray-50 transition-colors'
            >
              <span className='text-[14px] text-gray-500'>
                {(INGESTION_STAGES as Record<string, string>)[stage.stage] ||
                  stage.stage}
              </span>
              <span className='font-mono text-[14px] text-green-600 font-medium'>
                {stage.duration_ms.toFixed(0)}ms
              </span>
            </div>
          ))}
          <div className='h-px bg-gray-100 my-4' />
          <div className='flex justify-between items-center'>
            <span className='text-[14px] text-gray-500'>Total</span>
            <span className='font-mono text-[22px] font-semibold text-blue-600'>
              {uploadResult.timing.total_ms.toFixed(0)}ms
            </span>
          </div>
          <div className='flex gap-2 mt-4'>
            <span className='px-3 py-1 rounded-full bg-blue-50 text-blue-600 text-[11px] font-medium'>
              {uploadResult.ingestion_job.page_count} pages
            </span>
            <span className='px-3 py-1 rounded-full bg-purple-50 text-purple-600 text-[11px] font-medium'>
              {uploadResult.ingestion_job.chunk_count} chunks
            </span>
            <span className='px-3 py-1 rounded-full bg-green-50 text-green-600 text-[11px] font-medium'>
              {uploadResult.ingestion_job.status}
            </span>
          </div>
        </motion.div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════
   QUERY VIEW
   ═══════════════════════════════════════════════════ */
function QueryView({
  query,
  setQuery,
  querying,
  error,
  queryResponse,
  streamedAnswer,
  handleQuery,
  alpha,
  setAlpha,
  beta,
  setBeta,
  reranking,
  setReranking,
  hybrid,
  setHybrid,
}: {
  query: string;
  setQuery: (v: string) => void;
  querying: boolean;
  error: string | null;
  queryResponse: QueryResponse | null;
  streamedAnswer: string;
  handleQuery: () => void;
  alpha: number;
  setAlpha: (v: number) => void;
  beta: number;
  setBeta: (v: number) => void;
  reranking: boolean;
  setReranking: (v: boolean) => void;
  hybrid: boolean;
  setHybrid: (v: boolean) => void;
}) {
  return (
    <div className='grid grid-cols-1 lg:grid-cols-[1fr_280px] gap-8 items-start'>
      {/* Main */}
      <div>
        {/* Search */}
        <div className='relative mb-6'>
          <Search className='absolute left-5 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400' />
          <input
            type='text'
            placeholder='Ask anything across your documents…'
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleQuery()}
            disabled={querying}
            className='w-full py-4 pl-14 pr-28 bg-white border border-gray-200 rounded-2xl text-gray-900 text-[16px] outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 transition-all font-[inherit]'
          />
          <button
            onClick={handleQuery}
            disabled={querying || !query.trim()}
            className='absolute right-2 top-2 bottom-2 px-5 bg-blue-500 text-white text-[14px] font-medium rounded-xl border-none cursor-pointer disabled:opacity-30 hover:bg-blue-600 transition-colors'
          >
            {querying ? "…" : "Search"}
          </button>
        </div>

        {error && (
          <div className='p-4 rounded-2xl mb-6 bg-red-50 border border-red-100 text-red-600 text-[14px] flex items-center gap-2.5'>
            <Shield className='w-4 h-4 shrink-0' /> {error}
          </div>
        )}

        {/* Results */}
        <AnimatePresence>
          {(streamedAnswer || queryResponse) && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
            >
              {/* Answer */}
              <div className='rounded-3xl bg-white border border-gray-100 p-8 mb-6 shadow-sm'>
                <p className='text-[12px] font-semibold uppercase tracking-wider text-gray-400 mb-5'>
                  Answer
                </p>
                <p className='text-[16px] leading-[1.7] text-gray-800 whitespace-pre-wrap'>
                  {streamedAnswer || queryResponse?.response_text}
                </p>
              </div>

              {/* Citations */}
              {queryResponse?.citations &&
                queryResponse.citations.length > 0 && (
                  <div className='mb-6'>
                    <p className='text-[12px] font-semibold uppercase tracking-wider text-gray-400 mb-3'>
                      Sources
                    </p>
                    {queryResponse.citations.map((c, i) => (
                      <div
                        key={i}
                        className='flex gap-3 p-4 rounded-2xl bg-white border border-gray-100 border-l-2 border-l-purple-400 mb-1.5'
                      >
                        <Shield className='w-4 h-4 text-purple-500 shrink-0 mt-0.5' />
                        <div>
                          <p className='text-[14px] font-medium text-gray-900 mb-1'>
                            {c.document_name}{" "}
                            <span className='text-gray-400 font-normal'>
                              p.{c.page_number}
                            </span>
                          </p>
                          <p className='text-[13px] text-gray-500 leading-relaxed'>
                            {c.chunk_preview}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

              {/* Transparency */}
              {queryResponse && (
                <TransparencySection response={queryResponse} />
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Sidebar */}
      <div className='space-y-5'>
        {/* Hyperparameters */}
        <div className='rounded-3xl bg-white border border-gray-100 p-6 shadow-sm'>
          <p className='text-[12px] font-semibold uppercase tracking-wider text-gray-400 mb-5'>
            Hyperparameters
          </p>
          <SliderRow label='Alpha (Vector)' value={alpha} onChange={setAlpha} />
          <SliderRow label='Beta (Diversity)' value={beta} onChange={setBeta} />
          <div className='h-px bg-gray-100 my-4' />
          <ToggleRow
            label='Neural Reranking'
            checked={reranking}
            onChange={() => setReranking(!reranking)}
          />
          <div className='h-2' />
          <ToggleRow
            label='Hybrid Search'
            checked={hybrid}
            onChange={() => setHybrid(!hybrid)}
          />
        </div>

        {queryResponse?.confidence && (
          <ConfidenceCard confidence={queryResponse.confidence} />
        )}
        {queryResponse?.chunk_scores &&
          queryResponse.chunk_scores.length > 0 && (
            <HeatmapCard chunks={queryResponse.chunk_scores} />
          )}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════
   SMALL COMPONENTS
   ═══════════════════════════════════════════════════ */
function SliderRow({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <div className='mb-4'>
      <div className='flex justify-between mb-2'>
        <span className='text-[13px] text-gray-500'>{label}</span>
        <span className='font-mono text-[13px] text-gray-400'>
          {value.toFixed(2)}
        </span>
      </div>
      <input
        type='range'
        min='0'
        max='1'
        step='0.01'
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className='w-full accent-blue-500'
      />
    </div>
  );
}

function ToggleRow({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: () => void;
}) {
  return (
    <div
      onClick={onChange}
      className='flex items-center justify-between cursor-pointer py-1'
    >
      <span className='text-[14px] text-gray-600'>{label}</span>
      <div
        className={`w-11 h-6 rounded-full relative transition-colors duration-200 ${checked ? "bg-green-500" : "bg-gray-200"}`}
      >
        <motion.div
          animate={{ x: checked ? 20 : 3 }}
          transition={{ type: "spring", stiffness: 500, damping: 30 }}
          className='absolute top-[3px] w-[18px] h-[18px] rounded-full bg-white shadow-md'
        />
      </div>
    </div>
  );
}

function ConfidenceCard({ confidence }: { confidence: ConfidenceBreakdown }) {
  const pct = Math.round(confidence.overall * 100);
  return (
    <div className='rounded-3xl bg-white border border-gray-100 p-6 shadow-sm'>
      <p className='text-[12px] font-semibold uppercase tracking-wider text-gray-400 mb-4'>
        Confidence
      </p>
      <div className='flex items-end gap-2 mb-5'>
        <span className='text-[36px] font-semibold tracking-tight text-gray-900 leading-none'>
          {pct}%
        </span>
        <span className='text-[14px] text-gray-400 mb-1'>overall</span>
      </div>
      <BarRow
        label='Similarity'
        value={confidence.similarity_component}
        color='bg-purple-500'
      />
      <BarRow
        label='Reranker'
        value={confidence.reranker_component}
        color='bg-green-500'
      />
      <BarRow
        label='Agreement'
        value={confidence.agreement_component}
        color='bg-blue-500'
      />
      <BarRow
        label='Dispersion'
        value={confidence.dispersion_component}
        color='bg-yellow-400'
      />
    </div>
  );
}

function BarRow({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: string;
}) {
  return (
    <div className='mb-2.5'>
      <div className='flex justify-between mb-1'>
        <span className='text-[12px] text-gray-500'>{label}</span>
        <span className='font-mono text-[12px] text-gray-400'>
          {(value * 100).toFixed(0)}%
        </span>
      </div>
      <div className='h-1 bg-gray-100 rounded-full overflow-hidden'>
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${value * 100}%` }}
          transition={{ duration: 1 }}
          className={`h-full rounded-full ${color}`}
        />
      </div>
    </div>
  );
}

function HeatmapCard({ chunks }: { chunks: ChunkScore[] }) {
  const maxScore = Math.max(...chunks.map((c) => c.final_score), 0.01);
  return (
    <div className='rounded-3xl bg-white border border-gray-100 p-6 shadow-sm'>
      <p className='text-[12px] font-semibold uppercase tracking-wider text-gray-400 mb-4'>
        Retrieval Heatmap
      </p>
      <div className='flex gap-0.5 h-10'>
        {chunks.map((chunk, i) => {
          const intensity = chunk.final_score / maxScore;
          return (
            <motion.div
              key={i}
              initial={{ scaleY: 0 }}
              animate={{ scaleY: 1 }}
              transition={{ delay: i * 0.03 }}
              className='flex-1 rounded-sm origin-bottom'
              style={{
                background: `rgba(99,102,241,${0.1 + intensity * 0.9})`,
              }}
              title={`${chunk.document_name} p.${chunk.page_number}: ${chunk.final_score.toFixed(4)}`}
            />
          );
        })}
      </div>
      <div className='flex justify-between mt-2 text-[10px] text-gray-400'>
        <span>Low</span>
        <span>High</span>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════
   TRANSPARENCY SECTION
   ═══════════════════════════════════════════════════ */
function TransparencySection({ response }: { response: QueryResponse }) {
  return (
    <div className='space-y-6'>
      {/* Timing */}
      <div className='rounded-3xl bg-white border border-gray-100 p-8 shadow-sm'>
        <p className='text-[12px] font-semibold uppercase tracking-wider text-gray-400 mb-5'>
          Pipeline Timing
        </p>
        {response.timing.stages.map((stage, i) => (
          <div
            key={i}
            className='flex justify-between items-center py-3 px-4 rounded-xl hover:bg-gray-50 transition-colors'
          >
            <span className='text-[14px] text-gray-500'>
              {(PIPELINE_STAGES as Record<string, string>)[stage.stage] ||
                stage.stage}
            </span>
            <span className='font-mono text-[14px] text-green-600 font-medium'>
              {stage.duration_ms.toFixed(0)}ms
            </span>
          </div>
        ))}
        <div className='h-px bg-gray-100 my-4' />
        <div className='flex justify-between items-center'>
          <span className='text-[14px] text-gray-500'>Total</span>
          <span className='font-mono text-[22px] font-semibold text-blue-600'>
            {response.timing.total_ms.toFixed(0)}ms
          </span>
        </div>
      </div>

      {/* Metrics */}
      <div className='rounded-3xl bg-white border border-gray-100 p-8 shadow-sm'>
        <p className='text-[12px] font-semibold uppercase tracking-wider text-gray-400 mb-5'>
          Retrieval Metrics
        </p>
        <div className='grid grid-cols-3 gap-3'>
          <MetricCell
            label='Searched'
            value={response.retrieval_metrics.total_chunks_searched}
          />
          <MetricCell
            label='Vector'
            value={response.retrieval_metrics.vector_results_count}
          />
          <MetricCell
            label='BM25'
            value={response.retrieval_metrics.bm25_results_count}
          />
          <MetricCell
            label='Reranked'
            value={response.retrieval_metrics.reranked_count}
          />
          <MetricCell
            label='Context'
            value={response.retrieval_metrics.final_context_chunks}
          />
          <MetricCell
            label='Tokens'
            value={`${response.retrieval_metrics.token_budget_used}/${response.retrieval_metrics.token_budget_total}`}
          />
        </div>
      </div>
    </div>
  );
}

function MetricCell({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className='text-center p-4 rounded-2xl bg-gray-50'>
      <p className='font-mono text-[18px] font-semibold text-blue-600'>
        {value}
      </p>
      <p className='text-[10px] text-gray-400 mt-1 uppercase tracking-wider'>
        {label}
      </p>
    </div>
  );
}
