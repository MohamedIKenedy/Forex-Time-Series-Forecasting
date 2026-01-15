import React, { useState, useRef, useEffect } from 'react';
import type { TerminalOutput } from '../types';
import { Chart } from './Chart';
import './Terminal.css';

interface TerminalProps {
  outputs: TerminalOutput[];
  onCommand: (command: string) => Promise<void>;
  onTickerChange?: (chartIndex: number, newTicker: string) => Promise<void>;
  onPeriodChange?: (chartIndex: number, newPeriod: string) => Promise<void>;
}

export const Terminal: React.FC<TerminalProps> = ({ outputs, onCommand, onTickerChange, onPeriodChange }) => {
  const [command, setCommand] = useState('');
  const [commandHistory, setCommandHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const terminalRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const stickToBottomRef = useRef(true);
  const STICKY_SCROLL_THRESHOLD_PX = 48;

  useEffect(() => {
    const el = terminalRef.current;
    if (!el) return;
    if (!stickToBottomRef.current) return;
    el.scrollTop = el.scrollHeight;
  }, [outputs]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (command.trim()) {
      // Add to history
      setCommandHistory(prev => [...prev, command]);
      setHistoryIndex(-1);
      
      await onCommand(command);
      setCommand('');
    }
    inputRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (commandHistory.length === 0) return;
      
      const newIndex = historyIndex === -1 
        ? commandHistory.length - 1 
        : Math.max(0, historyIndex - 1);
      
      setHistoryIndex(newIndex);
      setCommand(commandHistory[newIndex]);
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (historyIndex === -1) return;
      
      const newIndex = historyIndex + 1;
      
      if (newIndex >= commandHistory.length) {
        setHistoryIndex(-1);
        setCommand('');
      } else {
        setHistoryIndex(newIndex);
        setCommand(commandHistory[newIndex]);
      }
    }
  };

  const handleContainerClick = () => {
    inputRef.current?.focus();
  };

  const handleTerminalScroll = () => {
    const el = terminalRef.current;
    if (!el) return;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    stickToBottomRef.current = distanceFromBottom <= STICKY_SCROLL_THRESHOLD_PX;
  };

  const getOutputClassName = (type: string) => {
    switch (type) {
      case 'command':
        return 'terminal-command';
      case 'error':
        return 'terminal-error';
      case 'success':
        return 'terminal-success';
      default:
        return 'terminal-output';
    }
  };

  return (
    <div className="terminal-container" onClick={handleContainerClick}>
      <div className="terminal-header">
        <div className="terminal-buttons">
          <div className="terminal-button close"></div>
          <div className="terminal-button minimize"></div>
          <div className="terminal-button maximize"></div>
        </div>
        <div className="terminal-title">forex@dashboard: ~/trading</div>
      </div>
      <div className="terminal-display" ref={terminalRef} onScroll={handleTerminalScroll}>
        {outputs.length === 0 && (
          <div className="terminal-welcome">
            <span className="highlight">ForexTerminal©</span> <span className="version">v1.0.0</span> - Developer Environment
            <br />
            <br />
            [OK] Starting system initialization...
            <br />
            [OK] Mounting virtual file systems...
            <br />
            [OK] Setting up network interfaces...
            <br />
            [OK] Starting system services...
            <br />
            <br />
            Type 'help' to see available commands
          </div>
        )}
        {outputs.map((output, index) => (
          <div key={output.id} className={`terminal-line ${getOutputClassName(output.type)}`}>
            {output.type === 'command' && <span className="prompt command">forex@dashboard:~$ </span>}
            <pre>{output.content}</pre>
            {output.plotData && (
              <Chart 
                data={output.plotData} 
                onTickerChange={(newTicker) => onTickerChange?.(index, newTicker)}
                onPeriodChange={(newPeriod) => onPeriodChange?.(index, newPeriod)}
                currentPeriod={output.plotData.period || '1d'}
              />
            )}
          </div>
        ))}
      </div>
      <form className="terminal-input-container" onSubmit={handleSubmit}>
        <span className="prompt command">forex@dashboard:~$ </span>
        <input
          ref={inputRef}
          type="text"
          className="terminal-input"
          value={command}
          onChange={(e) => setCommand(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder=""
          autoFocus
        />
      </form>
    </div>
  );
};
