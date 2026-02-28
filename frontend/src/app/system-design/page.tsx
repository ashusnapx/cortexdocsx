"use client";

import { useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import type { Components } from "react-markdown";
import mermaid from "mermaid";
import { ARCHITECTURE_CONTENT } from "./content";

/* ═══════════════════════════════════════════════════
   MERMAID DIAGRAM
   ═══════════════════════════════════════════════════ */
function MermaidDiagram({ chart }: { chart: string }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    const id = "m-" + Math.random().toString(36).slice(2, 9);
    ref.current.innerHTML = "";
    mermaid
      .render(id, chart)
      .then(({ svg }) => {
        if (ref.current) ref.current.innerHTML = svg;
      })
      .catch((err) => {
        if (ref.current)
          ref.current.innerHTML =
            '<pre style="color:#ff453a;font-size:12px;">' +
            err.message +
            "</pre>";
      });
  }, [chart]);

  return (
    <div
      ref={ref}
      style={{
        margin: "32px 0",
        display: "flex",
        justifyContent: "center",
        overflow: "auto",
      }}
    />
  );
}

/* ═══════════════════════════════════════════════════
   CUSTOM MARKDOWN COMPONENTS
   ═══════════════════════════════════════════════════ */
const mdComponents: Components = {
  h1: ({ children }) => (
    <h1
      style={{
        fontSize: 48,
        fontWeight: 700,
        letterSpacing: "-0.04em",
        lineHeight: 1.1,
        color: "#f5f5f7",
        marginBottom: 8,
        paddingBottom: 16,
        borderBottom: "1px solid rgba(255,255,255,0.08)",
      }}
    >
      {children}
    </h1>
  ),
  h2: ({ children }) => (
    <h2
      style={{
        fontSize: 32,
        fontWeight: 700,
        letterSpacing: "-0.03em",
        lineHeight: 1.2,
        color: "#f5f5f7",
        marginTop: 64,
        marginBottom: 16,
      }}
    >
      {children}
    </h2>
  ),
  h3: ({ children }) => (
    <h3
      style={{
        fontSize: 22,
        fontWeight: 600,
        letterSpacing: "-0.02em",
        lineHeight: 1.3,
        color: "#f5f5f7",
        marginTop: 40,
        marginBottom: 12,
      }}
    >
      {children}
    </h3>
  ),
  p: ({ children }) => (
    <p
      style={{
        fontSize: 16,
        lineHeight: 1.7,
        color: "#a1a1a6",
        marginBottom: 16,
      }}
    >
      {children}
    </p>
  ),
  strong: ({ children }) => (
    <strong style={{ color: "#f5f5f7", fontWeight: 600 }}>{children}</strong>
  ),
  a: ({ href, children }) => (
    <a
      href={href}
      style={{ color: "#2997ff", textDecoration: "none" }}
      onMouseEnter={(e) => (e.currentTarget.style.textDecoration = "underline")}
      onMouseLeave={(e) => (e.currentTarget.style.textDecoration = "none")}
    >
      {children}
    </a>
  ),
  blockquote: ({ children }) => (
    <blockquote
      style={{
        borderLeft: "3px solid #8b5cf6",
        paddingLeft: 20,
        margin: "24px 0",
        color: "#d1d1d6",
        fontStyle: "italic",
      }}
    >
      {children}
    </blockquote>
  ),
  hr: () => (
    <hr
      style={{
        border: "none",
        height: 1,
        background: "rgba(255,255,255,0.08)",
        margin: "48px 0",
      }}
    />
  ),
  ul: ({ children }) => (
    <ul style={{ paddingLeft: 24, margin: "16px 0", listStyleType: "disc" }}>
      {children}
    </ul>
  ),
  ol: ({ children }) => (
    <ol style={{ paddingLeft: 24, margin: "16px 0" }}>{children}</ol>
  ),
  li: ({ children }) => (
    <li
      style={{
        fontSize: 16,
        lineHeight: 1.7,
        color: "#a1a1a6",
        marginBottom: 6,
      }}
    >
      {children}
    </li>
  ),
  table: ({ children }) => (
    <div style={{ overflowX: "auto", margin: "24px 0" }}>
      <table
        style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}
      >
        {children}
      </table>
    </div>
  ),
  thead: ({ children }) => (
    <thead style={{ borderBottom: "2px solid rgba(255,255,255,0.12)" }}>
      {children}
    </thead>
  ),
  th: ({ children }) => (
    <th
      style={{
        textAlign: "left",
        padding: "12px 16px",
        fontSize: 12,
        fontWeight: 600,
        letterSpacing: "0.04em",
        textTransform: "uppercase",
        color: "#86868b",
      }}
    >
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td
      style={{
        padding: "12px 16px",
        borderBottom: "1px solid rgba(255,255,255,0.06)",
        color: "#d1d1d6",
        verticalAlign: "top",
      }}
    >
      {children}
    </td>
  ),
  tr: ({ children }) => (
    <tr
      style={{ transition: "background 0.15s" }}
      onMouseEnter={(e) =>
        (e.currentTarget.style.background = "rgba(255,255,255,0.02)")
      }
      onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
    >
      {children}
    </tr>
  ),
  code: ({ className, children }) => {
    const match = /language-(\w+)/.exec(className || "");
    const lang = match ? match[1] : "";

    if (lang === "mermaid") {
      return <MermaidDiagram chart={String(children).trim()} />;
    }

    // Inline code
    if (!className) {
      return (
        <code
          style={{
            background: "rgba(255,255,255,0.06)",
            padding: "2px 8px",
            borderRadius: 6,
            fontSize: 14,
            fontFamily: "'JetBrains Mono', monospace",
            color: "#e5c07b",
          }}
        >
          {children}
        </code>
      );
    }

    // Block code
    return (
      <code
        style={{
          display: "block",
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 13,
          lineHeight: 1.6,
          color: "#d1d1d6",
          whiteSpace: "pre",
          overflowX: "auto",
        }}
      >
        {children}
      </code>
    );
  },
  pre: ({ children }) => (
    <pre
      style={{
        background: "#1d1d1f",
        borderRadius: 16,
        padding: 24,
        margin: "24px 0",
        overflow: "auto",
        border: "1px solid rgba(255,255,255,0.06)",
      }}
    >
      {children}
    </pre>
  ),
};

/* ═══════════════════════════════════════════════════
   PAGE
   ═══════════════════════════════════════════════════ */
export default function SystemDesignPage() {
  useEffect(() => {
    mermaid.initialize({
      startOnLoad: false,
      theme: "dark",
      themeVariables: {
        primaryColor: "#2c2c2e",
        primaryTextColor: "#f5f5f7",
        primaryBorderColor: "#3a3a3c",
        lineColor: "#86868b",
        secondaryColor: "#1d1d1f",
        tertiaryColor: "#141414",
        fontFamily: "Inter, -apple-system, sans-serif",
        fontSize: "14px",
      },
    });
  }, []);

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#000",
        color: "#f5f5f7",
        fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
      }}
    >
      {/* Sticky breadcrumb */}
      <div
        style={{
          position: "sticky",
          top: 44,
          zIndex: 100,
          background: "rgba(0,0,0,0.72)",
          backdropFilter: "blur(20px)",
          WebkitBackdropFilter: "blur(20px)",
          borderBottom: "1px solid rgba(66,66,69,0.4)",
          padding: "10px 24px",
        }}
      >
        <div style={{ maxWidth: 860, margin: "0 auto" }}>
          <a
            href='/'
            style={{ color: "#2997ff", textDecoration: "none", fontSize: 14 }}
          >
            ← Back to Dashboard
          </a>
        </div>
      </div>

      {/* Article */}
      <article
        style={{
          maxWidth: 860,
          margin: "0 auto",
          padding: "60px 24px 120px",
        }}
      >
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          rehypePlugins={[rehypeRaw]}
          components={mdComponents}
        >
          {ARCHITECTURE_CONTENT}
        </ReactMarkdown>
      </article>
    </div>
  );
}
