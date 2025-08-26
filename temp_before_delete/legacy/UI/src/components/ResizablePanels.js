import React, { useRef, useState } from "react";
import "./styles/ResizablePanels.css";

function ResizablePanels({ leftContent, rightContent }) {
  const containerRef = useRef(null);
  // CTI Viewer on left (40%), Sigma Comparator on right (60%)
  const [leftWidth, setLeftWidth] = useState(40);

  const handleMouseDown = (e) => {
    e.preventDefault();
    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
  };

  const handleMouseMove = (e) => {
    const container = containerRef.current;
    const totalWidth = container.getBoundingClientRect().width;
    const newLeft = ((e.clientX - container.getBoundingClientRect().left) / totalWidth) * 100;
    // Allow range from 25% to 65% - right panel (Sigma Comparator) gets majority
    if (newLeft > 25 && newLeft < 65) setLeftWidth(newLeft);
  };

  const handleMouseUp = () => {
    document.removeEventListener("mousemove", handleMouseMove);
    document.removeEventListener("mouseup", handleMouseUp);
  };

  return (
    <div className="resizable-container" ref={containerRef}>
      <div className="resizable-left" style={{ width: `${leftWidth}%` }}>
        {leftContent}
      </div>
      <div className="resizable-divider" onMouseDown={handleMouseDown}></div>
      <div className="resizable-right" style={{ width: `${100 - leftWidth}%` }}>
        {rightContent}
      </div>
    </div>
  );
}

export default ResizablePanels;