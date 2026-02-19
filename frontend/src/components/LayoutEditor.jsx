import React, { useState, useEffect, useRef } from 'react';
import { v4 as uuidv4 } from 'uuid';
import './LayoutEditor.css';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

function LayoutEditor() {
    const [items, setItems] = useState([]);
    const [selectedItem, setSelectedItem] = useState(null);
    const [savedLayouts, setSavedLayouts] = useState({});
    const [layoutName, setLayoutName] = useState('');
    const [isBindingKey, setIsBindingKey] = useState(false);
    const [isSettingLabel, setIsSettingLabel] = useState(false);
    const [bindingPlayer, setBindingPlayer] = useState('default'); // 'default', 'player1', 'player2', etc.
    const [dragging, setDragging] = useState(false);
    const [draggedItem, setDraggedItem] = useState(null);
    const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
    const canvasRef = useRef(null);

    const keyToIconMap = {
        'ArrowUp': '↑',
        'ArrowDown': '↓',
        'ArrowLeft': '←',
        'ArrowRight': '→',
        'Enter': '⏎',
        ' ': '␣',
        'Shift': '⇧',
        'Control': '⌃',
        'Alt': '⌥',
        'Meta': '⌘',
        'Escape': '⎋',
        'Backspace': '⌫',
        'Tab': '⇥',
        'CapsLock': '⇪',
    };

    const fetchLayouts = async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/layouts`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            setSavedLayouts(data);
        } catch (error) {
            console.error("Error fetching layouts:", error);
            // Optionally, handle error state in UI
        }
    };

    useEffect(() => {
        fetchLayouts();
    }, []);

    useEffect(() => {
        const handleKeyDown = (event) => {
            if (isBindingKey && selectedItem) {
                event.preventDefault();
                handleItemPropertyChange('keybinds', {
                    ...selectedItemData.keybinds,
                    [bindingPlayer]: event.key
                });
                setIsBindingKey(false);
                setIsSettingLabel(true); // After keybind, user might want to set label
            } else if (isSettingLabel && selectedItem) {
                event.preventDefault();
                const icon = keyToIconMap[event.key] || event.key;
                handleItemPropertyChange('icon', icon);
                setIsSettingLabel(false);
            }
        };

        if (isBindingKey || isSettingLabel) {
            window.addEventListener('keydown', handleKeyDown);
        }

        return () => {
            window.removeEventListener('keydown', handleKeyDown);
        };
    }, [isBindingKey, isSettingLabel, selectedItem]);


    const onAddItem = () => {
        const newItem = {
            i: uuidv4(),
            x: 0,
            y: 0,
            icon: '',
            keybinds: {
                default: '',
            },
        };
        setItems([...items, newItem]);
    };

    const onRemoveItem = (i) => {
        setItems(items.filter((item) => item.i !== i));
        if (selectedItem === i) {
            setSelectedItem(null);
        }
    };

    const handleItemClick = (i) => {
        setSelectedItem(i);
        setIsBindingKey(false);
        setIsSettingLabel(false);
        setBindingPlayer('default'); // Reset binding player when selecting new item
    };

    const handleItemPropertyChange = (prop, value) => {
        const newItems = items.map((item) => {
            if (item.i === selectedItem) {
                return { ...item, [prop]: value };
            }
            return item;
        });
        setItems(newItems);
    };

    const handleDragStart = (e, item) => {
        if (e.button !== 0) return; // Only drag with left mouse button
        setDragging(true);
        setDraggedItem(item.i);
        const canvasRect = canvasRef.current.getBoundingClientRect();
        setDragOffset({
            x: e.clientX - canvasRect.left - item.x,
            y: e.clientY - canvasRect.top - item.y,
        });
        e.stopPropagation();
    };

    const handleDrag = (e) => {
        if (!dragging) return;
        const canvasRect = canvasRef.current.getBoundingClientRect();
        let newX = e.clientX - canvasRect.left - dragOffset.x;
        let newY = e.clientY - canvasRect.top - dragOffset.y;

        // Clamp position to be within the canvas
        newX = Math.max(0, Math.min(newX, canvasRect.width - 80)); // Assuming item width is 80
        newY = Math.max(0, Math.min(newY, canvasRect.height - 80)); // Assuming item height is 80


        setItems(prevItems =>
            prevItems.map(item =>
                item.i === draggedItem ? { ...item, x: newX, y: newY } : item
            )
        );
    };

    const handleDragEnd = () => {
        setDragging(false);
        setDraggedItem(null);
    };

    const saveLayout = async () => {
        if (!layoutName) {
            alert('Please enter a name for the layout.');
            return;
        }

        try {
            const response = await fetch(`${API_BASE_URL}/layouts/${layoutName}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ items }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            await response.json(); // Read response to ensure connection is closed
            alert(`Custom layout "${layoutName}" saved!`);
            fetchLayouts(); // Refresh the list of saved layouts
        } catch (error) {
            console.error("Error saving layout:", error);
            alert("Failed to save layout.");
        }
    };

    const loadLayout = async (name) => {
        try {
            const response = await fetch(`${API_BASE_URL}/layouts/${name}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const layoutToLoad = await response.json();
            if (layoutToLoad && layoutToLoad.items) {
                setItems(layoutToLoad.items.map(item => ({...item})));
                setLayoutName(name);
            } else {
                alert(`Layout "${name}" not found or invalid.`);
            }
        } catch (error) {
            console.error("Error loading layout:", error);
            alert("Failed to load layout.");
        }
    };

    const deleteLayout = async (name) => {
        if (!window.confirm(`Are you sure you want to delete layout "${name}"?`)) {
            return;
        }

        try {
            const response = await fetch(`${API_BASE_URL}/layouts/${name}`, {
                method: 'DELETE',
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            await response.json(); // Read response to ensure connection is closed
            alert(`Layout "${name}" deleted!`);
            fetchLayouts(); // Refresh the list of saved layouts
            setLayoutName('');
            setItems([]);
        } catch (error) {
            console.error("Error deleting layout:", error);
            alert("Failed to delete layout.");
        }
    };

    const selectedItemData = items.find(item => item.i === selectedItem);

    return (
        <div className="layout-editor-container">
            <div className="editor-controls">
                <h2>Layout Controls</h2>
                <button onClick={onAddItem}>Add Button</button>
                <hr />
                <h3>Save/Load Layout</h3>
                <input
                    type="text"
                    placeholder="Layout Name"
                    value={layoutName}
                    onChange={(e) => setLayoutName(e.target.value)}
                />
                <button onClick={saveLayout}>Save Layout</button>
                <hr />
                <select onChange={(e) => loadLayout(e.target.value)} value={layoutName || ""}>
                    <option value="" disabled>Load a layout</option>
                    {Object.keys(savedLayouts).map((name) => (
                        <option key={name} value={name}>{name}</option>
                    ))}
                </select>
                {layoutName && <button onClick={() => deleteLayout(layoutName)} disabled={layoutName === "Arrows"}>Delete Current Layout</button>}
                 <hr/>
                {selectedItemData && (
                    <div className="item-properties">
                        <h3>Edit Button: {selectedItemData.i.substring(0, 5)}...</h3>
                        <p>Icon: {selectedItemData.icon}</p>
                        <button onClick={() => setIsSettingLabel(true)}>
                            {isSettingLabel ? 'Press key for label...' : 'Set Label'}
                        </button>
                        <hr/>
                        <h4>Keybinds:</h4>
                        {['default', 'player1', 'player2', 'player3', 'player4'].map(player => (
                            <div key={player}>
                                <p>{player}: {selectedItemData.keybinds?.[player] || 'N/A'}</p>
                                <button onClick={() => { setBindingPlayer(player); setIsBindingKey(true); }}>
                                    Set {player} Keybind
                                </button>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            <div
                className="editor-grid"
                onMouseMove={handleDrag}
                onMouseUp={handleDragEnd}
                onMouseLeave={handleDragEnd}
            >
                <div className="layout-canvas" ref={canvasRef}>
                    {items.map((item) => (
                        <div
                            key={item.i}
                            className={`draggable-item ${selectedItem === item.i ? 'selected' : ''}`}
                            style={{ transform: `translate(${item.x}px, ${item.y}px)` }}
                            onMouseDown={(e) => {
                                handleItemClick(item.i);
                                handleDragStart(e, item);
                            }}
                        >
                            <button className="remove" onClick={(e) => {e.stopPropagation(); onRemoveItem(item.i)}}>x</button>
                            <div className="button-content">
                                {item.icon ? <span>{item.icon}</span> : <span>{item.keybinds?.default || 'N/A'}</span>}
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}

export default LayoutEditor;
