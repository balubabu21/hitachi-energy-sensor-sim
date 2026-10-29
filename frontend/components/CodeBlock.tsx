"use client";

import { Highlight, themes } from "prism-react-renderer";

export function CodeBlock({ code, language }: { code: string; language: string }) {
  return (
    <Highlight theme={themes.vsDark} code={code.replace(/\n$/, "")} language={language}>
      {({ className, style, tokens, getLineProps, getTokenProps }) => (
        <pre className={`code ${className}`} style={style}>
          {tokens.map((line, i) => (
            <div key={i} {...getLineProps({ line })}>
              <span className="ln">{i + 1}</span>
              {line.map((token, k) => (
                <span key={k} {...getTokenProps({ token })} />
              ))}
            </div>
          ))}
        </pre>
      )}
    </Highlight>
  );
}

export function CopyButton({ text, label = "Copy" }: { text: string; label?: string }) {
  return (
    <button
      className="btn ghost"
      onClick={(e) => {
        const btn = e.currentTarget;
        navigator.clipboard?.writeText(text).then(() => {
          btn.textContent = "Copied";
          setTimeout(() => (btn.textContent = label), 1200);
        });
      }}
    >
      {label}
    </button>
  );
}
