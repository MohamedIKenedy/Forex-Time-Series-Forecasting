import { startInstantStreaming, startStreaming, stopStreaming, getStreamingStatus, getForexData, getKafkaDiagram, getKafkaHealth, getKafkaTopics, getInference, getInferenceMetadata } from './api';
import type { TerminalOutput } from './types';

export class CommandHandler {
  private outputs: TerminalOutput[] = [];
  private idCounter = 0;

  private generateId(): string {
    return `cmd_${Date.now()}_${this.idCounter++}`;
  }

  async executeCommand(command: string): Promise<TerminalOutput> {
    const parts = command.trim().split(' ');
    const action = parts[0].toLowerCase();
    const args = parts.slice(1);

    let output: TerminalOutput = {
      id: this.generateId(),
      content: '',
      type: 'output',
    };

    try {
      switch (action) {
        case 'start':
          output = await this.handleStart(args);
          break;
        case 'stop':
          output = await this.handleStop();
          break;
        case 'status':
          output = await this.handleStatus();
          break;
        case 'options':
          output = await this.handleOptions(args);
          break;
        case 'plot':
          output = await this.handlePlot(args);
          break;
        case 'kafka':
          output = await this.handleKafka(args);
          break;
        case 'tail':
        case 'last':
          output = await this.handleTail(args);
          break;
        case 'infer':
          output = await this.handleInference(args);
          break;
        case 'help':
          output = this.handleHelp();
          break;
        case 'clear':
          this.outputs = [];
          output.content = 'Terminal cleared';
          output.type = 'success';
          output.clearTerminal = true;
          break;
        default:
          output.content = `Command not found: ${action}\nType 'help' for available commands`;
          output.type = 'error';
      }
    } catch (error) {
      output.content = error instanceof Error ? error.message : 'Unknown error occurred';
      output.type = 'error';
    }

    this.outputs.push(output);
    return output;
  }

  private formatTable(rows: Array<Record<string, any>>): string {
    if (!rows.length) return '(no rows)';

    const columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume'];
    const colWidths: Record<string, number> = {
      Date: 24,
      Open: 16,
      High: 16,
      Low: 16,
      Close: 16,
      Volume: 12,
    };

    const fmt = (value: any, col: string) => {
      if (value === undefined || value === null) return '';
      if (typeof value === 'number') {
        if (col === 'Volume') return String(Math.trunc(value));
        // Show lots of decimals so tiny changes are visible.
        return value.toFixed(12);
      }
      return String(value);
    };

    const pad = (text: string, col: string) => {
      const w = colWidths[col] ?? 12;
      // Right-align numeric-looking columns.
      const isNumericCol = col !== 'Date';
      return isNumericCol ? text.padStart(w) : text.padEnd(w);
    };

    const header = columns.map((c) => pad(c, c)).join(' | ');
    const sep = columns.map((c) => '-'.repeat(colWidths[c] ?? 12)).join('-|-');
    const body = rows
      .map((row) => columns.map((c) => pad(fmt(row[c], c), c)).join(' | '))
      .join('\n');

    return `${header}\n${sep}\n${body}`;
  }

  private async handleStart(args: string[]): Promise<TerminalOutput> {
    // Default to instant mode so the UI feels realtime.
    // Users can still switch via `options hourly`.
    await startInstantStreaming();
    return {
      id: this.generateId(),
      content: '✓ Instant streaming started for all forex tickers',
      type: 'success',
    };
  }

  private async handleStop(): Promise<TerminalOutput> {
    await stopStreaming();
    return {
      id: this.generateId(),
      content: '✓ Streaming stopped',
      type: 'success',
    };
  }

  private async handleStatus(): Promise<TerminalOutput> {
    const status = await getStreamingStatus();
    const content = `Streaming Status:
Status: ${status.status}
Tickers: ${status.tickers?.join(', ') || 'None'}
Last Update: ${status.lastUpdate || 'N/A'}`;

    return {
      id: this.generateId(),
      content,
      type: 'output',
    };
  }

  private async handleOptions(args: string[]): Promise<TerminalOutput> {
    if (args.length === 0 || !['instant', 'hourly', 'daily'].includes(args[0])) {
      return {
        id: this.generateId(),
        content: 'Usage: options <mode>\nModes: instant (1s updates) | hourly (1h updates) | daily (1d updates)',
        type: 'error'
      };
    }
    
    const mode = args[0];
    const endpoint = mode === 'instant' ? 'start_instant_streaming' : mode === 'daily' ? 'start_daily_streaming' : 'start_streaming';
    
    try {
      await stopStreaming();
      const response = await fetch(`http://localhost:8000/stream/${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      const data = await response.json();
      return {
        id: this.generateId(),
        content: `✓ Switched to ${mode} mode`,
        type: 'success'
      };
    } catch (error) {
      return {
        id: this.generateId(),
        content: `Failed to switch mode: ${error instanceof Error ? error.message : 'Unknown error'}`,
        type: 'error'
      };
    }
  }

  private async handlePlot(args: string[]): Promise<TerminalOutput> {
    if (args.length === 0) {
      return {
        id: this.generateId(),
        content: 'Error: Please specify a ticker symbol\nUsage: plot <ticker> [period]\nPeriods: 1d, 5d, 1mo, 3mo, 6mo, 1y\nExample: plot EURUSD=X 1mo',
        type: 'error',
      };
    }

    const ticker = args[0].trim().toUpperCase();
    const period = args[1] || '1d'; // Default to 1 day
    try {
      // Make 1d charts feel realtime by ensuring instant streaming is on.
      if (period === '1d') {
        try {
          await startInstantStreaming();
        } catch {
          // Non-fatal: the chart can still render historical data.
        }
      }

      const data = await getForexData(ticker, period);
      
      // Extract plot data
      const dataSource = data.data;
      const dates = dataSource.map((d: any) => d.Date);
      const prices = dataSource.map((d: any) => d.Close);
      
      const content = `${ticker} - ${data.streaming ? 'Live Stream' : 'Historical Data'} [${period.toUpperCase()}]`;

      return {
        id: this.generateId(),
        content,
        type: 'success',
        plotData: {
          ticker,
          dates,
          prices,
          streaming: data.streaming,
          period,
          interval: data.interval,
          latest: data.latest
        }
      };
    } catch (error) {
      return {
        id: this.generateId(),
        content: `Failed to fetch data for ${ticker}: ${error instanceof Error ? error.message : 'Unknown error'}`,
        type: 'error',
      };
    }
  }

  private async handleTail(args: string[]): Promise<TerminalOutput> {
    if (args.length === 0) {
      return {
        id: this.generateId(),
        content: 'Usage: tail <ticker> [n] [period]\nExamples:\n  tail EURUSD=X\n  tail EURUSD=X 20\n  tail EURUSD=X 20 1d\n  tail EURUSD=X 1mo 30',
        type: 'error',
      };
    }

    const ticker = args[0].trim().toUpperCase();

    // Allow: tail <ticker> [n] [period] OR tail <ticker> [period] [n]
    let n = 10;
    let period = '1d';

    if (args[1]) {
      const maybeN = Number(args[1]);
      if (Number.isFinite(maybeN) && maybeN > 0) {
        n = Math.min(200, Math.floor(maybeN));
        if (args[2]) period = args[2];
      } else {
        period = args[1];
        if (args[2]) {
          const maybeN2 = Number(args[2]);
          if (Number.isFinite(maybeN2) && maybeN2 > 0) n = Math.min(200, Math.floor(maybeN2));
        }
      }
    }

    try {
      const data = await getForexData(ticker, period);
      const rows = Array.isArray(data?.data) ? data.data : [];
      const lastRows = rows.slice(-n);

      const table = this.formatTable(lastRows);
      const meta = `Ticker: ${ticker}\nPeriod: ${data?.period ?? period}  Interval: ${data?.interval ?? 'n/a'}\nRows: showing last ${lastRows.length} of ${rows.length}`;

      return {
        id: this.generateId(),
        content: `${meta}\n\n${table}`,
        type: 'output',
      };
    } catch (error) {
      return {
        id: this.generateId(),
        content: `Failed to fetch tail for ${ticker}: ${error instanceof Error ? error.message : 'Unknown error'}`,
        type: 'error',
      };
    }
  }

  private async handleInference(args: string[]): Promise<TerminalOutput> {
    if (args.length === 0) {
      return {
        id: this.generateId(),
        content: `Usage: infer <ticker> [lookback]
Lookback sets how many recent records are used (default 200).`,
        type: 'error',
      };
    }

    const ticker = args[0].trim().toUpperCase();
    let lookback = 200;
    if (args[1]) {
      const parsed = Number(args[1]);
      if (!Number.isFinite(parsed) || parsed <= 0) {
        return {
          id: this.generateId(),
          content: 'Lookback must be a positive number',
          type: 'error',
        };
      }
      lookback = Math.max(50, Math.min(1000, Math.floor(parsed)));
    }

    try {
      const prediction = await getInference(ticker, lookback);
      let metadata: any = null;
      let metadataNotice = '';
      try {
        metadata = await getInferenceMetadata(ticker);
      } catch (metaError) {
        metadataNotice = metaError instanceof Error ? metaError.message : 'Metadata fetch failed';
      }

      const lines: string[] = [
        `Inference result for ${ticker} (lookback=${lookback})`,
        `  Direction: ${prediction.direction}`,
        `  Predicted log return: ${prediction.predicted_log_return.toFixed(8)}`,
      ];

      if (metadata) {
        lines.push('', 'Model metadata:');
        if (metadata.prediction_target) {
          lines.push(`  Target: ${metadata.prediction_target}`);
        }
        if (metadata.horizon) {
          lines.push(`  Horizon: ${metadata.horizon}`);
        }
        if (metadata.lookback) {
          lines.push(`  Model lookback: ${metadata.lookback}`);
        }
        if (metadata.fold) {
          lines.push(`  Fold: ${metadata.fold}`);
        }
        if (metadata.n_features) {
          lines.push(`  Feature count: ${metadata.n_features}`);
        }
        if (Array.isArray(metadata.model_formats) && metadata.model_formats.length) {
          lines.push(`  Formats: ${metadata.model_formats.join(', ')}`);
        }
        if (metadata.scaler) {
          lines.push(`  Scaler: ${metadata.scaler}`);
        }
        if (metadata.performance_status) {
          lines.push(`  Performance: ${metadata.performance_status}`);
        }
        const metrics = metadata.metrics ?? {};
        const metricEntries = Object.entries(metrics)
          .map(([key, value]) => `${key}: ${typeof value === 'number' ? value.toFixed(6) : value}`);
        if (metricEntries.length) {
          lines.push(`  Metrics: ${metricEntries.join(', ')}`);
        }
        const features = Array.isArray(metadata.features) ? metadata.features : [];
        if (features.length) {
          const preview = features.slice(0, 10).join(', ');
          const rest = Math.max(0, features.length - 10);
          lines.push(`  Features (${features.length}): ${preview}${rest ? `, ... (+${rest} more)` : ''}`);
        }
      } else if (metadataNotice) {
        lines.push('', `Model metadata unavailable: ${metadataNotice}`);
      }

      return {
        id: this.generateId(),
        content: lines.join('\n'),
        type: 'success',
      };
    } catch (error) {
      return {
        id: this.generateId(),
        content: `Inference failed for ${ticker}: ${error instanceof Error ? error.message : 'Unknown error'}`,
        type: 'error',
      };
    }
  }

  private async handleKafka(args: string[]): Promise<TerminalOutput> {
    const sub = (args[0] || 'diagram').toLowerCase();

    const help =
      'Kafka commands:\n' +
      '  kafka diagram              - Show architecture diagram\n' +
      '  kafka health               - Check broker connectivity\n' +
      '  kafka topics [prefix]      - List topics (optionally filter by prefix)\n' +
      '\nExamples:\n' +
      '  kafka topics\n' +
      '  kafka topics instant_\n' +
      '  kafka health\n';

    try {
      if (sub === 'help') {
        return { id: this.generateId(), content: help, type: 'output' };
      }

      if (sub === 'diagram') {
        const data = await getKafkaDiagram();
        return {
          id: this.generateId(),
          content: data?.diagram || '(no diagram)',
          type: 'output',
        };
      }

      if (sub === 'health') {
        const data = await getKafkaHealth();
        const content = `Kafka Health\nOK: ${data?.ok ?? false}\nBrokers: ${(data?.brokers || []).join(', ') || 'n/a'}\nTopics: ${data?.topics_count ?? 'n/a'}`;
        return {
          id: this.generateId(),
          content,
          type: data?.ok ? 'success' : 'error',
        };
      }

      if (sub === 'topics') {
        const prefix = args[1];
        const data = await getKafkaTopics(prefix);
        const topics = Array.isArray(data?.topics) ? data.topics : [];

        const col1 = 46;
        const col2 = 10;
        const header = `${'TOPIC'.padEnd(col1)} | ${'PARTITIONS'.padStart(col2)}`;
        const sep = `${'-'.repeat(col1)}-+-${'-'.repeat(col2)}`;
        const body = topics
          .map((t: any) => {
            const topic = String(t.topic ?? '').slice(0, col1);
            const partitions = String(t.partitions ?? '');
            return `${topic.padEnd(col1)} | ${partitions.padStart(col2)}`;
          })
          .join('\n');

        const meta = `Brokers: ${(data?.brokers || []).join(', ') || 'n/a'}\nTopics: ${topics.length}${prefix ? ` (prefix=${prefix})` : ''}`;

        return {
          id: this.generateId(),
          content: `${meta}\n\n${header}\n${sep}${body ? `\n${body}` : ''}`,
          type: 'output',
        };
      }

      return {
        id: this.generateId(),
        content: `Unknown kafka subcommand: ${sub}\n\n${help}`,
        type: 'error',
      };
    } catch (error) {
      return {
        id: this.generateId(),
        content: `Kafka command failed: ${error instanceof Error ? error.message : 'Unknown error'}\n\n${help}`,
        type: 'error',
      };
    }
  }

  private handleHelp(): TerminalOutput {
    const helpText = `
Available Commands:
  start               - Start streaming data (instant mode)
  stop                - Stop streaming
  status              - Show streaming status
  options <mode>      - Switch streaming mode (instant|hourly)
  plot [ticker]       - Display plot for a specific ticker
  tail <ticker> [...] - Show last N rows (dataframe-like)
    infer <ticker> [lookback] - Run inference and show model metadata
  kafka ...            - Kafka architecture commands
  exit|quit|logout    - Return to console
  help                - Show this help message
  clear               - Clear terminal output

Examples:
  > start
  > options instant
  > plot EURUSD=X
  > tail EURUSD=X 20 1d
  > kafka diagram
  > kafka topics instant_
  > status
  > stop
  > infer EURUSD=X
  > exit
`;
    return {
      id: this.generateId(),
      content: helpText,
      type: 'output',
    };
  }

  getOutputs(): TerminalOutput[] {
    return this.outputs;
  }

  clearOutputs(): void {
    this.outputs = [];
  }
}
