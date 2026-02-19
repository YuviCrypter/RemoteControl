import React, { useState, useEffect } from 'react';
import { QRCodeSVG } from 'qrcode.react';
import { Link } from 'react-router-dom';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

function JoinScreen() {
    const [numPlayers, setNumPlayers] = useState(1);
    const [selectedLayout, setSelectedLayout] = useState('');
    const [savedLayouts, setSavedLayouts] = useState({});
    const [showQRCodes, setShowQRCodes] = useState(false);

    useEffect(() => {
        const fetchLayouts = async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/layouts`);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const data = await response.json();
                setSavedLayouts(data);

                const firstLayout = Object.keys(data)[0];
                if (firstLayout) {
                    setSelectedLayout(firstLayout);
                }
            } catch (error) {
                console.error("Error fetching layouts:", error);
            }
        };

        fetchLayouts();
    }, []);

    const generateLinks = () => {
        setShowQRCodes(true);
    };

    const getBaseUrl = () => {
        const url = window.location.origin;
        return url.endsWith('/') ? url.slice(0, -1) : url;
    }

    if (showQRCodes) {
        const links = [];
        for (let i = 1; i <= numPlayers; i++) {
            const remoteUrl = `${getBaseUrl()}/remote/${i}?layout=${encodeURIComponent(selectedLayout)}`;
            links.push({
                player: i,
                url: remoteUrl,
            });
        }

        return (
            <div>
                <h2>Scan QR Code to Join</h2>
                <div style={{ display: 'flex', flexWrap: 'wrap' }}>
                    {links.map((link) => (
                        <div key={link.player} style={{ margin: '20px', textAlign: 'center' }}>
                            <p>Player {link.player}</p>
                            <QRCodeSVG value={link.url} />
                            <p><a href={link.url} target="_blank" rel="noopener noreferrer">Open Link</a></p>
                        </div>
                    ))}
                </div>
                <button onClick={() => setShowQRCodes(false)}>Back</button>
            </div>
        );
    }

    return (
        <div>
            <h1>Join Game</h1>
            <div>
                <label>Number of Players:</label>
                <input
                    type="number"
                    min="1"
                    max="4"
                    value={numPlayers}
                    onChange={(e) => setNumPlayers(parseInt(e.target.value))}
                />
            </div>
            <div>
                <label>Select Layout:</label>
                <select
                    value={selectedLayout}
                    onChange={(e) => setSelectedLayout(e.target.value)}
                    disabled={Object.keys(savedLayouts).length === 0}
                >
                    {Object.keys(savedLayouts).length === 0 ? (
                        <option>No layouts available</option>
                    ) : (
                        Object.keys(savedLayouts).map((name) => (
                            <option key={name} value={name}>
                                {name}
                            </option>
                        ))
                    )}
                </select>
            </div>
            <button onClick={generateLinks} disabled={!selectedLayout}>
                Generate Join Links
            </button>
            <br />
            <Link to="/editor">Go to Layout Editor</Link>
        </div>
    );
}

export default JoinScreen;
