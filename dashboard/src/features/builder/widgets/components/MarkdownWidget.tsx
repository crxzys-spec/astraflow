import clsx from "clsx";
import type { MouseEvent, WheelEvent } from "react";
import { useMemo } from "react";
import type { WidgetRendererProps } from "../registry";
import { toStringValue } from "./utils";

const escapeHtml = (input: string) =>
  input
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");

const renderInline = (input: string) => {
  let text = escapeHtml(input);
  text = text.replace(/`([^`]+)`/g, "<code>$1</code>");
  text = text.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  text = text.replace(/~~([^~]+)~~/g, "<del>$1</del>");
  text = text.replace(/\*([^*]+)\*/g, "<em>$1</em>");
  text = text.replace(/_([^_]+)_/g, "<em>$1</em>");
  text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
  return text;
};

const renderCodeBlock = (block: string) => {
  const lines = block.replace(/\r\n/g, "\n").split("\n");
  let language = "";
  if (lines.length > 1 && /^[a-z0-9_-]+$/i.test(lines[0].trim())) {
    language = lines.shift()!.trim();
  }
  const code = escapeHtml(lines.join("\n").trimEnd());
  const langAttr = language ? ` data-language="${escapeHtml(language)}"` : "";
  return `<pre class="wf-widget__markdown-pre"><button class="wf-widget__markdown-copy" type="button">Copy</button><code${langAttr}>${code}</code></pre>`;
};

const renderTextBlock = (block: string) => {
  const lines = block.replace(/\r\n/g, "\n").split("\n");
  const output: string[] = [];
  let listType: "ul" | "ol" | null = null;

  const closeList = () => {
    if (listType) {
      output.push(`</${listType}>`);
      listType = null;
    }
  };

  lines.forEach((rawLine) => {
    const line = rawLine.trim();
    if (!line) {
      closeList();
      return;
    }
    const headingMatch = line.match(/^(#{1,6})\s+(.*)$/);
    if (headingMatch) {
      closeList();
      const level = headingMatch[1].length;
      output.push(`<h${level}>${renderInline(headingMatch[2])}</h${level}>`);
      return;
    }
    const orderedMatch = line.match(/^\d+\.\s+(.*)$/);
    if (orderedMatch) {
      if (listType !== "ol") {
        closeList();
        listType = "ol";
        output.push("<ol>");
      }
      output.push(`<li>${renderInline(orderedMatch[1])}</li>`);
      return;
    }
    const unorderedMatch = line.match(/^[-*]\s+(.*)$/);
    if (unorderedMatch) {
      if (listType !== "ul") {
        closeList();
        listType = "ul";
        output.push("<ul>");
      }
      output.push(`<li>${renderInline(unorderedMatch[1])}</li>`);
      return;
    }
    closeList();
    output.push(`<p>${renderInline(line)}</p>`);
  });

  closeList();
  return output.join("");
};

const renderMarkdown = (input: string) => {
  const trimmed = input.trim();
  if (!trimmed) {
    return '<p class="wf-widget__markdown-empty">No content.</p>';
  }
  const segments = input.split(/```/);
  const blocks = segments.map((segment, index) => {
    if (index % 2 === 1) {
      return renderCodeBlock(segment);
    }
    return renderTextBlock(segment);
  });
  return blocks.join("");
};

export const MarkdownWidget = ({ widget, value, readOnly }: WidgetRendererProps) => {
  const markdown = toStringValue(value);
  const rendered = useMemo(() => renderMarkdown(markdown), [markdown]);
  const className = clsx("wf-widget__markdown", {
    "wf-widget__markdown--readonly": readOnly,
  });

  const handleCopyClick = (event: MouseEvent<HTMLDivElement>) => {
    const target = event.target as HTMLElement | null;
    const button = target?.closest(".wf-widget__markdown-copy") as HTMLButtonElement | null;
    if (!button) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    const pre = button.closest("pre");
    const code = pre?.querySelector("code");
    const text = code?.textContent ?? "";
    if (!text) {
      return;
    }
    const updateButton = () => {
      button.textContent = "Copied";
      button.setAttribute("data-copied", "true");
      window.setTimeout(() => {
        if (!button.isConnected) {
          return;
        }
        button.textContent = "Copy";
        button.removeAttribute("data-copied");
      }, 1200);
    };
    if (navigator.clipboard?.writeText) {
      navigator.clipboard
        .writeText(text)
        .then(updateButton)
        .catch(() => {
          const textarea = document.createElement("textarea");
          textarea.value = text;
          textarea.style.position = "fixed";
          textarea.style.opacity = "0";
          document.body.appendChild(textarea);
          textarea.select();
          try {
            document.execCommand("copy");
            updateButton();
          } finally {
            document.body.removeChild(textarea);
          }
        });
      return;
    }
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.select();
    try {
      document.execCommand("copy");
      updateButton();
    } finally {
      document.body.removeChild(textarea);
    }
  };

  const handleWheel = (event: WheelEvent<HTMLDivElement>) => {
    event.stopPropagation();
  };

  return (
    <div className="wf-widget wf-widget--markdown">
      <label className="wf-widget__label wf-widget__label--stacked">
        {widget.label}
        <div
          className={className}
          onWheel={handleWheel}
          onWheelCapture={handleWheel}
          onClick={handleCopyClick}
          dangerouslySetInnerHTML={{ __html: rendered }}
        />
      </label>
    </div>
  );
};
