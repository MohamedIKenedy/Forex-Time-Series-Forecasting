import { useState, useCallback, useEffect } from 'react'
import { Terminal } from './components/Terminal'
import { LandingPage } from './components/LandingPage'
import { StatsPage } from './components/StatsPage'
import { TickersPage } from './components/TickersPage'
import { CommandHandler } from './commandHandler'
import { wsClient } from './websocket'
import { ensureInstantStreaming, getForexData } from './api'
import type { TerminalOutput } from './types'
import './App.css'

const commandHandler = new CommandHandler()
let commandIdCounter = 0

type Page = 'landing' | 'terminal' | 'stats' | 'tickers'

function App() {
  const [currentPage, setCurrentPage] = useState<Page>('landing')
  const [outputs, setOutputs] = useState<TerminalOutput[]>([
    {
      id: '0',
      content: 'Welcome to Forex Dashboard Terminal\nType \'help\' for available commands',
      type: 'output'
    }
  ])

  useEffect(() => {
    wsClient.connect()

    const unsubscribe = wsClient.subscribe(async (message) => {
      if (message.type === 'price_update') {
        const ticker = String(message.ticker ?? '').trim().toUpperCase()
        if (!ticker) return

        const newDate = message.data?.timestamp || new Date().toISOString()
        const newPrice = message.data?.close
        if (typeof newPrice !== 'number' || Number.isNaN(newPrice)) return

        const parseDate = (ts: string) => {
          const d = new Date(ts)
          return Number.isNaN(d.getTime()) ? null : d
        }

        const bucketKey = (ts: string, interval?: string) => {
          const d = parseDate(ts)
          if (!d) return String(ts)

          // Use UTC for stable bucketing.
          const year = d.getUTCFullYear()
          const month = String(d.getUTCMonth() + 1).padStart(2, '0')
          const day = String(d.getUTCDate()).padStart(2, '0')
          const hour = String(d.getUTCHours()).padStart(2, '0')
          const minute = d.getUTCMinutes()

          if (!interval || interval === '1d') return `${year}-${month}-${day}`
          if (interval.endsWith('h')) return `${year}-${month}-${day}T${hour}:00`
          if (interval.endsWith('m')) {
            const step = Number.parseInt(interval.replace('m', ''), 10)
            const bucketMinute = Number.isFinite(step) && step > 1
              ? Math.floor(minute / step) * step
              : minute
            return `${year}-${month}-${day}T${hour}:${String(bucketMinute).padStart(2, '0')}`
          }

          // Fallback: treat as full timestamp.
          return d.toISOString()
        }

        const normalizeTimestampForInterval = (ts: string, interval?: string) => {
          const d = parseDate(ts)
          if (!d) return ts

          // For display, we store a normalized timestamp that matches the candle bucket.
          // This prevents the chart from adding multiple points for the same candle.
          const utc = new Date(d.getTime())
          if (!interval || interval === '1d') {
            return utc.toISOString().slice(0, 10)
          }
          if (interval.endsWith('h')) {
            utc.setUTCMinutes(0, 0, 0)
            return utc.toISOString()
          }
          if (interval.endsWith('m')) {
            const step = Number.parseInt(interval.replace('m', ''), 10)
            const mins = utc.getUTCMinutes()
            const bucketMinute = Number.isFinite(step) && step > 1
              ? Math.floor(mins / step) * step
              : mins
            utc.setUTCMinutes(bucketMinute, 0, 0)
            return utc.toISOString()
          }
          return utc.toISOString()
        }

        const maxPointsFor = (period?: string, interval?: string) => {
          const p = (period || '').toLowerCase()
          const i = (interval || '').toLowerCase()

          // Defaults: keep enough points to resemble Yahoo's full-period view.
          // Cap to prevent runaway memory usage.
          const hardCap = 6000

          const periodMinutes: Record<string, number> = {
            '1d': 1 * 24 * 60,
            '5d': 5 * 24 * 60,
            '1mo': 30 * 24 * 60,
            '3mo': 90 * 24 * 60,
            '6mo': 180 * 24 * 60,
            '1y': 365 * 24 * 60,
          }

          const minutes = periodMinutes[p]
          if (i.endsWith('m')) {
            const step = Number.parseInt(i.replace('m', ''), 10)
            const stepMins = Number.isFinite(step) && step > 0 ? step : 1
            if (minutes) return Math.min(hardCap, Math.ceil(minutes / stepMins))
            // Unknown period: show a reasonable recent window.
            return 2000
          }

          if (i === 'tick') return 2000
          if (i.endsWith('h')) {
            if (minutes) return Math.min(hardCap, Math.ceil(minutes / 60))
            return 2000
          }

          // Daily/weekly data.
          if (p === '1y') return 400
          if (p === '6mo') return 220
          if (p === '3mo') return 120
          if (p === '1mo') return 40
          if (p === '5d') return 120
          if (p === '1d') return 2000

          return 2000
        }

        setOutputs(prev => {
          return prev.map((out) => {
            if (!out.plotData) return out
            if (String(out.plotData.ticker ?? '').trim().toUpperCase() !== ticker) return out

            const toEpochMs = (value: string) => {
              if (!value) return null

              // Handle date-only strings (treat as UTC midnight for stable ordering).
              if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
                const ms = Date.parse(`${value}T00:00:00Z`)
                return Number.isFinite(ms) ? ms : null
              }

              // Normalize common pandas/yfinance timestamp strings: "YYYY-MM-DD HH:mm:ss+00:00" -> ISO.
              let normalized = value
              if (normalized.includes(' ') && !normalized.includes('T')) {
                normalized = normalized.replace(' ', 'T')
              }

              // If there is a time but no timezone marker, assume UTC.
              const hasTimezone = /([zZ]|[+-]\d{2}:?\d{2})$/.test(normalized)
              const hasTime = /T\d{2}:\d{2}/.test(normalized)
              if (hasTime && !hasTimezone) {
                normalized = `${normalized}Z`
              }

              const ms = Date.parse(normalized)
              return Number.isFinite(ms) ? ms : null
            }

            const parsePartition = (partition: string) => {
              const parts = partition.split('_')
              if (parts.length < 2) return { period: undefined as string | undefined, interval: undefined as string | undefined }
              const period = parts[0]
              const interval = parts.slice(1).join('_')
              return { period, interval }
            }

            const intervalType = (interval?: string) => {
              if (!interval) return 'unknown'
              if (interval.endsWith('m')) return 'minute'
              if (interval.endsWith('h')) return 'hour'
              if (interval.endsWith('d')) return 'day'
              if (interval.endsWith('wk')) return 'week'
              if (interval.endsWith('mo')) return 'month'
              return 'unknown'
            }

            // Avoid mixing totally different candle types (e.g. hourly into 1-minute charts),
            // but don't drop updates just because the backend used a different *period* key.
            const msgPartition = typeof message.partition === 'string' ? parsePartition(message.partition) : null
            const chartInterval = out.plotData.interval
            const msgInterval = msgPartition?.interval
            const chartType = intervalType(chartInterval)
            const msgType = intervalType(msgInterval)

            if (chartInterval && msgInterval && chartType !== 'unknown' && msgType !== 'unknown' && chartType !== msgType) {
              return out
            }

            const chartIntervalForState = out.plotData.interval
            const intervalForBucketing = (msgInterval === 'tick')
              ? (chartIntervalForState ?? '1m')
              : (msgInterval ?? chartIntervalForState)

            const normalizedDate = normalizeTimestampForInterval(newDate, intervalForBucketing)
            const lastDate = out.plotData.dates[out.plotData.dates.length - 1]

            const sameBucketAsLast =
              typeof lastDate === 'string' &&
              bucketKey(lastDate, intervalForBucketing) === bucketKey(normalizedDate, intervalForBucketing)

            const baseDates = sameBucketAsLast ? out.plotData.dates.slice(0, -1) : out.plotData.dates
            const basePrices = sameBucketAsLast ? out.plotData.prices.slice(0, -1) : out.plotData.prices

            const mergedEntries = baseDates.map((date, idx) => ({ date, price: basePrices[idx] }))
            mergedEntries.push({ date: normalizedDate, price: newPrice })

            const sortedEntries = mergedEntries.sort((a, b) => {
              const da = toEpochMs(a.date)
              const db = toEpochMs(b.date)
              if (da == null && db == null) return 0
              if (da == null) return 1
              if (db == null) return -1
              return da - db
            })

            // Deduplicate identical timestamps after sorting (keep the latest value).
            const deduped: Array<{ date: string; price: number }> = []
            for (const entry of sortedEntries) {
              const last = deduped[deduped.length - 1]
              if (last && last.date === entry.date) {
                last.price = entry.price
              } else {
                deduped.push({ ...entry })
              }
            }

            const maxPoints = maxPointsFor(out.plotData.period, chartIntervalForState ?? msgInterval)
            const trimmedEntries = deduped.slice(-maxPoints)
            const updatedDates = trimmedEntries.map(entry => entry.date)
            const updatedPrices = trimmedEntries.map(entry => entry.price)

            return {
              ...out,
              plotData: {
                ...out.plotData,
                dates: updatedDates,
                prices: updatedPrices,
                streaming: true,
                interval: chartIntervalForState,
                latest: message.data,
              },
            }
          })
        })
      }
    })

    return () => {
      unsubscribe()
      wsClient.disconnect()
    }
  }, [])

  const handleCommand = useCallback(async (command: string) => {
    const trimmedCommand = command.trim().toLowerCase();
    
    // Handle exit commands
    if (trimmedCommand === 'exit' || trimmedCommand === 'quit' || trimmedCommand === 'logout') {
      setCurrentPage('landing');
      return;
    }
    
    // Handle clear command
    if (trimmedCommand === 'clear') {
      setOutputs([]);
      return;
    }
    
    setOutputs(prev => [...prev, {
      id: `cmd_input_${Date.now()}_${commandIdCounter++}`,
      content: command,
      type: 'command'
    }])

    const result = await commandHandler.executeCommand(command)
    setOutputs(prev => [...prev, result])
  }, [])

  const handleTickerChange = useCallback(async (chartIndex: number, newTicker: string) => {
    try {
      const currentPeriod = outputs[chartIndex]?.plotData?.period || '1d';
      const normalizedTicker = String(newTicker ?? '').trim().toUpperCase();
      if (!normalizedTicker) return
      const data = await getForexData(normalizedTicker, currentPeriod);
      const dataSource = data.data;
      const dates = dataSource.map((d: any) => d.Date);
      const prices = dataSource.map((d: any) => d.Close);

      setOutputs(prev => {
        const updated = [...prev];
        if (updated[chartIndex]?.plotData) {
          updated[chartIndex] = {
            ...updated[chartIndex],
            content: `${normalizedTicker} - ${data.streaming ? 'Live Stream' : 'Historical Data'} [${currentPeriod.toUpperCase()}]`,
            plotData: {
              ticker: normalizedTicker,
              dates,
              prices,
              streaming: data.streaming,
              period: currentPeriod,
              interval: data.interval,
              latest: data.latest
            }
          };
        }
        return updated;
      });
    } catch (error) {
      console.error('Failed to change ticker:', error);
    }
  }, [outputs]);

  const handlePeriodChange = useCallback(async (chartIndex: number, newPeriod: string) => {
    try {
      // For 1d we want 1-minute candles; ensure backend is in instant mode.
      if (newPeriod === '1d') {
        await ensureInstantStreaming();
      }

      const currentTicker = outputs[chartIndex]?.plotData?.ticker || 'EURUSD=X';
      const normalizedTicker = String(currentTicker ?? '').trim().toUpperCase();
      const data = await getForexData(normalizedTicker, newPeriod);
      const dataSource = data.data;
      const dates = dataSource.map((d: any) => d.Date);
      const prices = dataSource.map((d: any) => d.Close);

      setOutputs(prev => {
        const updated = [...prev];
        if (updated[chartIndex]?.plotData) {
          updated[chartIndex] = {
            ...updated[chartIndex],
            content: `${normalizedTicker} - ${data.streaming ? 'Live Stream' : 'Historical Data'} [${newPeriod.toUpperCase()}]`,
            plotData: {
              ticker: normalizedTicker,
              dates,
              prices,
              streaming: data.streaming,
              period: newPeriod,
              interval: data.interval,
              latest: data.latest
            }
          };
        }
        return updated;
      });
    } catch (error) {
      console.error('Failed to change period:', error);
    }
  }, [outputs]);

  return (
    <div className="app-container">
      {currentPage === 'landing' && (
        <LandingPage onNavigate={(page) => setCurrentPage(page)} />
      )}
      {currentPage === 'terminal' && (
        <Terminal 
          outputs={outputs} 
          onCommand={handleCommand} 
          onTickerChange={handleTickerChange} 
          onPeriodChange={handlePeriodChange} 
        />
      )}
      {currentPage === 'stats' && (
        <StatsPage onBack={() => setCurrentPage('landing')} />
      )}
      {currentPage === 'tickers' && (
        <TickersPage 
          onBack={() => setCurrentPage('landing')} 
          onSelectTicker={(ticker) => {
            console.log('Selected ticker:', ticker);
            setCurrentPage('terminal');
          }}
        />
      )}
    </div>
  )
}

export default App
