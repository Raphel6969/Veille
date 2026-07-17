import { useState, useRef, useEffect } from "react";

interface DropdownProps {
  value: string;
  options: string[];
  onChange: (value: string) => void;
  disabled?: boolean;
}

export function Dropdown({ value, options, onChange, disabled }: DropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div ref={containerRef} style={{ position: "relative", display: "inline-block", width: "160px", userSelect: "none" }}>
      <div 
        className="glass-button"
        style={{ 
          display: "flex", 
          justifyContent: "space-between", 
          alignItems: "center",
          opacity: disabled ? 0.5 : 1,
          pointerEvents: disabled ? "none" : "auto",
          width: "100%",
          padding: "6px 12px"
        }}
        onClick={() => setIsOpen(!isOpen)}
      >
        <span>{value}</span>
        <span style={{ fontSize: "10px", marginLeft: "8px", color: "var(--text-secondary)" }}>▼</span>
      </div>
      
      {isOpen && (
        <div className="glass-panel" style={{ 
          position: "absolute", 
          top: "100%", 
          left: 0, 
          right: 0, 
          marginTop: "4px", 
          padding: "4px",
          zIndex: 50,
          maxHeight: "200px",
          overflowY: "auto",
          boxShadow: "0 10px 40px rgba(0, 0, 0, 0.5)"
        }}>
          {options.map((opt) => (
            <div 
              key={opt}
              className={`dropdown-item ${opt === value ? "active" : ""}`}
              onClick={() => {
                onChange(opt);
                setIsOpen(false);
              }}
            >
              {opt}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
