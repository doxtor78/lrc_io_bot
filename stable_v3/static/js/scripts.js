document.addEventListener('DOMContentLoaded', () => {
    console.log('Scripts.js loaded at', new Date().toISOString());

    // Elements
    const chartContainer = document.getElementById('chart');
    const statusElement = document.getElementById('status');
    const retryButton = document.getElementById('retry-btn');

    if (!chartContainer) {
        console.error('Error: #chart div missing');
        if (statusElement) statusElement.textContent = 'Error: Chart container not found';
        return;
    }
    console.log('Chart container OK, size:', chartContainer.offsetWidth, 'x', chartContainer.offsetHeight);

    if (!statusElement) {
        console.warn('Warning: #status div missing');
    } else {
        statusElement.textContent = 'Setting up chart...';
    }

    if (!retryButton) {
        console.warn('Warning: #retry-btn missing');
    }

    // Debug LightweightCharts object
    console.log('LightweightCharts object:', window.LightweightCharts);
    if (!window.LightweightCharts) {
        console.error('Error: LightweightCharts is undefined');
        if (statusElement) statusElement.textContent = 'Error: Lightweight Charts library not loaded';
        return;
    }

    if (!window.LightweightCharts.createChart) {
        console.error('Error: createChart method not found in LightweightCharts');
        console.log('Available methods:', Object.keys(window.LightweightCharts));
        if (statusElement) statusElement.textContent = 'Error: Chart creation method not available';
        return;
    }

    let chart, candlestickSeries, volumeSeries;
    let currentBinSize = '1m';

    // Function to fetch and render data
    function loadChartData() {
        console.log('Fetching /historical-data at', new Date().toISOString());
        if (statusElement) statusElement.textContent = 'Fetching chart data...';

        fetch(`/historical-data?binSize=${currentBinSize}`)
            .then(response => {
                console.log('Fetch response:', response.status, response.statusText);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('Data received:', data.slice(0, 2)); // Log first 2 candles

                if (!data || !Array.isArray(data) || data.length === 0) {
                    console.warn('No data received');
                    if (statusElement) statusElement.textContent = 'No data available. Simulate trades on BitMEX Testnet or retry.';
                    return;
                }

                // Minimal validation
                const isValid = data.every(item => 
                    typeof item.time === 'number' &&
                    typeof item.open === 'number' &&
                    typeof item.high === 'number' &&
                    typeof item.low === 'number' &&
                    typeof item.close === 'number' &&
                    typeof item.volume === 'number'
                );

                if (!isValid) {
                    console.error('Invalid data format:', data.slice(0, 2));
                    if (statusElement) statusElement.textContent = 'Error: Invalid data format';
                    return;
                }

                console.log('Rendering data:', data.length, 'candles');
                candlestickSeries.setData(data);
                volumeSeries.setData(data.map(d => ({
                    time: d.time,
                    value: d.volume * 0.1,
                    color: d.close >= d.open ? '#26a69a' : '#ef5350'
                })));
                chart.timeScale().fitContent();
                console.log('Chart rendered');
                if (statusElement) statusElement.textContent = `Chart loaded: ${data.length} candles`;
            })
            .catch(error => {
                console.error('Fetch error:', error);
                if (statusElement) statusElement.textContent = `Error fetching data: ${error.message}. Click Retry.`;
            });
    }

    try {
        // Initialize chart
        console.log('Creating chart...');
        chart = window.LightweightCharts.createChart(chartContainer, {
            width: chartContainer.offsetWidth,
            height: chartContainer.offsetHeight,
            layout: {
                background: { type: 'solid', color: '#ffffff' },
                textColor: '#333',
            },
            timeScale: {
                timeVisible: true,
                secondsVisible: false,
            },
        });
        console.log('Chart created');

        // Minimize the height of the volume candles
        chart.priceScale('volume').applyOptions({
            scaleMargins: {
                top: 0.8,    // 80% of chart is for price
                bottom: 0,   // 20% of chart is for volume
            },
        });

        // Debug chart object
        console.log('Chart object:', chart);
        console.log('Available chart methods:', Object.keys(chart));

        // Verify addCandlestickSeries
        if (typeof chart.addCandlestickSeries !== 'function') {
            throw new Error('addCandlestickSeries is not a function');
        }

        // Add candlestick series
        candlestickSeries = chart.addCandlestickSeries({
            upColor: '#26a69a',
            downColor: '#ef5350',
            borderVisible: false,
            wickUpColor: '#26a69a',
            wickDownColor: '#ef5350',
        });
        console.log('Candlestick series created');

        // Add volume series
        volumeSeries = chart.addHistogramSeries({
            color: '#26a69a',
            priceFormat: { type: 'volume' },
            priceScaleId: 'volume',
        });
        console.log('Volume series created');

        // Test render with single candle
        console.log('Testing chart render...');
        const testCandle = [{
            time: Math.floor(Date.now() / 1000) - 60,
            open: 60000,
            high: 60010,
            low: 59990,
            close: 60005,
            volume: 1000
        }];
        candlestickSeries.setData(testCandle);
        volumeSeries.setData(testCandle.map(d => ({
            time: d.time,
            value: d.volume * 0.1,
            color: d.close >= d.open ? '#26a69a' : '#ef5350'
        })));
        chart.timeScale().fitContent();
        console.log('Test candle rendered');
        if (statusElement) statusElement.textContent = 'Test candle loaded. Fetching real data...';

        // Load real data
        loadChartData();

        // Retry button
        if (retryButton) {
            retryButton.addEventListener('click', () => {
                console.log('Retry button clicked');
                loadChartData();
            });
        }

        // WebSocket for real-time updates
        console.log('Connecting to WebSocket...');
        const ws = new WebSocket('wss://ws-testnet.bitmex.com/realtime');

        let currentCandle = null;
        let lastTimestamp = null;

        ws.onopen = () => {
            console.log('WebSocket connected');
            ws.send(JSON.stringify({
                op: 'subscribe',
                args: ['trade:XBTUSD']
            }));
        };

        ws.onmessage = (event) => {
            console.log('WebSocket message at', new Date().toISOString());
            const message = JSON.parse(event.data);
            if (message.table !== 'trade' || !message.data) return;
            console.log('Trade data:', message.data);

            message.data.forEach(trade => {
                const tradeTime = new Date(trade.timestamp).getTime() / 1000;
                const price = trade.price;
                const volume = trade.size;
                const minute = Math.floor(tradeTime / 60) * 60;

                if (!currentCandle || minute !== lastTimestamp) {
                    if (currentCandle) {
                        candlestickSeries.update(currentCandle);
                        volumeSeries.update({
                            time: currentCandle.time,
                            value: (currentCandle.volume || 0) * 0.1,
                            color: currentCandle.close >= currentCandle.open ? '#26a69a' : '#ef5350'
                        });
                        console.log('Saved candle:', currentCandle);
                    }
                    currentCandle = {
                        time: minute,
                        open: price,
                        high: price,
                        low: price,
                        close: price,
                        volume: volume
                    };
                    lastTimestamp = minute;
                } else {
                    currentCandle.high = Math.max(currentCandle.high, price);
                    currentCandle.low = Math.min(currentCandle.low, price);
                    currentCandle.close = price;
                    currentCandle.volume = (currentCandle.volume || 0) + volume;
                    candlestickSeries.update(currentCandle);
                    volumeSeries.update({
                        time: currentCandle.time,
                        value: currentCandle.volume * 0.1,
                        color: currentCandle.close >= currentCandle.open ? '#26a69a' : '#ef5350'
                    });
                    console.log('Updated candle:', currentCandle);
                }
            });
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            if (statusElement) statusElement.textContent = 'WebSocket failed. Data may not update.';
        };

        ws.onclose = () => {
            console.log('WebSocket closed');
            if (statusElement) statusElement.textContent = 'WebSocket disconnected. Click Retry.';
        };

        // Add event listeners for timeframe buttons
        const timeframeButtons = document.querySelectorAll('#timeframe-buttons button');
        const chartInfoTimeframe = document.getElementById('current-timeframe');
        timeframeButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                currentBinSize = btn.getAttribute('data-bin-size');
                if (chartInfoTimeframe) {
                    chartInfoTimeframe.textContent = btn.textContent;
                }
                loadChartData();
            });
        });
    } catch (error) {
        console.error('Chart init error:', error);
        console.error('Error stack:', error.stack);
        if (statusElement) statusElement.textContent = `Chart failed: ${error.message}`;
    }
});