import React, { useState, useEffect, useRef } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import './RemoteControl.css';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

function RemoteControl() {
    let { playerId: urlPlayerId } = useParams();
    const [searchParams] = useSearchParams();
    const [layout, setLayout] = useState(null);
    const ws = useRef(null);
    const playerId = parseInt(urlPlayerId, 10); // Ensure player ID is an integer

    useEffect(() => {
        const layoutName = searchParams.get('layout');
        if (!layoutName) {
            console.error("Layout name not provided in URL.");
            return;
        }

        const fetchLayout = async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/layouts/${layoutName}`);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const fetchedLayout = await response.json();
                if (fetchedLayout && fetchedLayout.items) {
                    setLayout(fetchedLayout);
                } else {
                    console.error(`Layout "${layoutName}" not found or invalid.`);
                }
            } catch (error) {
                console.error("Error fetching layout:", error);
            }
        };

        fetchLayout();

        // Setup WebSocket connection
        const wsUrl = `ws://${window.location.hostname}:8000/ws/${playerId}?layout=${layoutName}`;
        ws.current = new WebSocket(wsUrl);

        ws.current.onopen = () => {
            console.log(`Player ${playerId} connected to WebSocket for layout ${layoutName}.`);
        };

        ws.current.onclose = () => {
            console.log(`Player ${playerId} disconnected from WebSocket.`);
        };
        
        ws.current.onerror = (error) => {
            console.error("WebSocket Error:", error);
        };

        return () => {
            if (ws.current) {
                ws.current.close();
            }
        };
    }, [urlPlayerId, searchParams]);

    const handleButtonPress = (itemId) => {
        if (ws.current && ws.current.readyState === WebSocket.OPEN) {
            ws.current.send(JSON.stringify({ itemId: itemId, action: 'down' }));
        }
    };

    const handleButtonRelease = (itemId) => {
        if (ws.current && ws.current.readyState === WebSocket.OPEN) {
            ws.current.send(JSON.stringify({ itemId: itemId, action: 'up' }));
        }
    };
    
    // Prevent context menu on long press on mobile
    useEffect(() => {
        const handleContextMenu = (e) => e.preventDefault();
        document.addEventListener('contextmenu', handleContextMenu);
        return () => {
            document.removeEventListener('contextmenu', handleContextMenu);
        };
    }, []);

    if (!layout) {
        return <div className="remote-control-container"><div>Loading layout or layout not found...</div></div>;
    }

    return (
        <div className="remote-control-container">
            <div className="remote-canvas">
                {layout.items.map((item) => (
                    <div
                        key={item.i}
                        className="remote-button"
                        style={{ left: `${item.x}px`, top: `${item.y}px` }}
                        onTouchStart={() => handleButtonPress(item.i)}
                        onTouchEnd={() => handleButtonRelease(item.i)}
                        onMouseDown={() => handleButtonPress(item.i)}
                        onMouseUp={() => handleButtonRelease(item.i)}
                    >
                        <div className="button-content">
                            {item.icon ? <span>{item.icon}</span> : <span>{item.keybinds?.default || 'N/A'}</span>}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}

export default RemoteControl;
