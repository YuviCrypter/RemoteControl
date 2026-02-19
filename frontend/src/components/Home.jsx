import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import LayoutEditor from './LayoutEditor';
import JoinScreen from './JoinScreen';
import RemoteControl from './RemoteControl';

function Home() {
    return (
        <div>
            <h1>Remote Control</h1>
            <nav>
                <ul>
                    <li>
                        <Link to="/editor">Layout Editor</Link>
                    </li>
                    <li>
                        <Link to="/join">Join Game</Link>
                    </li>
                </ul>
            </nav>
        </div>
    );
}

function AppRouter() {
  return (
    <Router>
        <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/editor" element={<LayoutEditor />} />
            <Route path="/join" element={<JoinScreen />} />
            <Route path="/remote/:playerId" element={<RemoteControl />} />
        </Routes>
    </Router>
  );
}

export default AppRouter;
