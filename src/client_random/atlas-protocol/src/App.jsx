import React, { useState, useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Html, PerspectiveCamera, Stars, Float, Text, MeshReflectorMaterial } from '@react-three/drei';
import { EffectComposer, Bloom, Vignette, Noise } from '@react-three/postprocessing';
import * as THREE from 'three';
import {
  Upload,
  CheckCircle2,
  AlertTriangle,
  Wallet,
  Activity,
  Search,
  Scan,
  Database,
  X
} from 'lucide-react';
import './App.css';

// --- MOCK DATA & CONSTANTS ---
const INITIAL_BALANCE = 124.50;
const BOUNTY_REWARD = 15.00;

const LOCATIONS = [
  { id: 1, name: "The Grand Cafe", position: [0, 0.5, 0], status: 'stale', type: 'cafe' },
  { id: 2, name: "Blackwell's Books", position: [-4, 0.5, -2], status: 'fresh', type: 'shop' },
  { id: 3, name: "Radcliffe Camera", position: [3, 0.5, -3], status: 'fresh', type: 'landmark' },
  { id: 4, name: "Covered Market", position: [2, 0.5, 4], status: 'fresh', type: 'market' },
  { id: 5, name: "Ashmolean Museum", position: [-3, 0.5, 5], status: 'fresh', type: 'museum' },
];

// --- 3D COMPONENTS ---

const GridFloor = () => {
  return (
    <group position={[0, -0.02, 0]}>
      {/* Reflective Dark Floor */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <planeGeometry args={[50, 50]} />
        <MeshReflectorMaterial
          blur={[300, 100]}
          resolution={1024}
          mixBlur={1}
          mixStrength={40}
          roughness={1}
          depthScale={1.2}
          minDepthThreshold={0.4}
          maxDepthThreshold={1.4}
          color="#101010"
          metalness={0.5}
        />
      </mesh>
      {/* Grid Overlay */}
      <gridHelper args={[50, 50, 0x303030, 0x101010]} position={[0, 0.01, 0]} />
    </group>
  );
};

const DataBeacon = ({ position, status, name, onClick, isSelected }) => {
  const meshRef = useRef();
  const [hovered, setHover] = useState(false);

  // Colors
  const freshColor = new THREE.Color("#10b981"); // Emerald
  const staleColor = new THREE.Color("#ef4444"); // Red
  const color = status === 'stale' ? staleColor : freshColor;

  // Selection/Hover visual logic
  const isActive = hovered || isSelected;

  useFrame((state) => {
    if (meshRef.current) {
      // Basic rotation
      meshRef.current.rotation.y += 0.01;
      meshRef.current.rotation.x = Math.sin(state.clock.elapsedTime) * 0.1;

      // Pulse scaling
      if (status === 'stale' || isActive) {
        const pulse = 1 + Math.sin(state.clock.elapsedTime * 3) * (isActive ? 0.1 : 0.05);
        meshRef.current.scale.setScalar(pulse);
      } else {
        meshRef.current.scale.setScalar(1);
      }
    }
  });

  return (
    <group position={position}>
      <Float speed={2} rotationIntensity={0.2} floatIntensity={0.5} floatingRange={[0, 0.5]}>
        {/* Main Beacon Mesh */}
        <mesh
          ref={meshRef}
          onClick={(e) => { e.stopPropagation(); onClick(); }}
          onPointerOver={() => setHover(true)}
          onPointerOut={() => setHover(false)}
          castShadow
          receiveShadow
        >
          {status === 'stale' ? (
            // Stale: Octahedron (Spiky)
            <octahedronGeometry args={[0.7, 0]} />
          ) : (
            // Fresh: Box (Stable)
            <boxGeometry args={[0.6, 0.6, 0.6]} />
          )}

          {/* Glowing Material */}
          <meshStandardMaterial
            color={color}
            emissive={color}
            emissiveIntensity={isActive ? 3 : 1} // BRIGHT GLOW on select
            toneMapped={false} // Crucial for Bloom
            roughness={0.2}
            metalness={0.8}
            wireframe={status === 'fresh' && !isActive}
          />
        </mesh>

        {/* Inner core for wireframes */}
        {(status === 'fresh' && !isActive) && (
          <mesh>
            <boxGeometry args={[0.4, 0.4, 0.4]} />
            <meshBasicMaterial color={color} />
          </mesh>
        )}
      </Float>

      {/* Floating UI Label in 3D Space */}
      {(hovered || isSelected || status === 'stale') && (
        <Html position={[0, 1.5, 0]} center distanceFactor={12} zIndexRange={[100, 0]}>
          <div className={`beacon-label ${status}`}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              {status === 'stale' && <AlertTriangle size={12} />}
              {name}
            </div>
          </div>
        </Html>
      )}

      {/* Ground Ring Marker */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.48, 0]}>
        <ringGeometry args={[0.3, 0.45, 32]} />
        <meshBasicMaterial color={color} opacity={0.5} transparent side={THREE.DoubleSide} toneMapped={false} />
      </mesh>

      {/* Vertical light beam for selected */}
      {isSelected && (
        <mesh position={[0, 5, 0]}>
          <cylinderGeometry args={[0.02, 0.4, 10, 8]} />
          <meshBasicMaterial color={color} transparent opacity={0.2} side={THREE.DoubleSide} depthWrite={false} blending={THREE.AdditiveBlending} />
        </mesh>
      )}
    </group>
  );
};

// --- UI COMPONENTS ---

const DashboardHeader = ({ balance }) => (
  <div className="hud-header">
    <div className="hud-left">
      <div className="brand-title">
        <Database size={24} color="#10b981" />
        BOUNTY GO
      </div>
    </div>

    <div className="hud-right">
      <div className="wallet-widget">
        <div className="wallet-icon">
          <Wallet size={20} />
        </div>
        <div className="wallet-info">
          <label>Wallet Balance</label>
          <div className="wallet-balance">${balance.toFixed(2)}</div>
        </div>
      </div>
    </div>
  </div>
);

const BountyPanel = ({ selectedLocation, onClose, onVerify }) => {
  const [formData, setFormData] = useState({ image: null, description: '' });

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFormData(prev => ({ ...prev, image: e.target.files[0] }));
    }
  };

  const handleDescriptionChange = (e) => {
    setFormData(prev => ({ ...prev, description: e.target.value }));
  };

  const [isVerifying, setIsVerifying] = useState(false);
  const [step, setStep] = useState(0); // 0: Idle, 1: Scanning, 2: Cross-Ref, 3: Success

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!formData.image) return; // Prevent submit without image

    setIsVerifying(true);
    setStep(1);

    // Simulate AI Process - 4 Seconds Total
    // 0s: Start Scanning
    setTimeout(() => setStep(2), 1500); // 1.5s: Cross-referencing
    setTimeout(() => {
      setStep(3); // 3.0s: Verdict/Success
    }, 3000);

    setTimeout(() => {
      onVerify(selectedLocation.id);
      setIsVerifying(false);
      setFormData({ image: null, description: '' }); // Reset form
      setStep(0);
    }, 4000); // 4.0s: Finish
  };

  if (!selectedLocation) return null;

  return (
    <div className="bounty-panel" key={selectedLocation.id}>
      <div className="panel-header">
        <div className="panel-title">
          <div className={`status-dot ${selectedLocation.status}`} />
          <span>{selectedLocation.name.toUpperCase()}</span>
        </div>
        <button onClick={onClose} className="btn-close">
          <X size={16} />
        </button>
      </div>

      <div className="panel-content">
        <div className="info-row">
          <div className="info-block">
            <label>Network Status</label>
            <div className={`value ${selectedLocation.status}`}>
              {selectedLocation.status === 'stale' ? 'CRITICAL_STALENESS' : 'VERIFIED_ACTIVE'}
            </div>
            {selectedLocation.status === 'stale' && (
              <div style={{ fontSize: '10px', color: '#666', marginTop: '2px' }}>Last Verified: 45 Days Ago</div>
            )}
          </div>

          {selectedLocation.status === 'stale' && (
            <div className="info-block" style={{ textAlign: 'right' }}>
              <label>Bounty</label>
              <div className="value bounty">${BOUNTY_REWARD.toFixed(2)}</div>
            </div>
          )}
        </div>

        {/* Action Area */}
        {selectedLocation.status === 'stale' && !isVerifying && (
          <form className="bounty-form" onSubmit={handleSubmit}>

            {/* Image Upload */}
            <label className={`file-drop-area ${formData.image ? 'active' : ''}`}>
              <input type="file" accept="image/*" onChange={handleFileChange} />
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
                <Upload size={24} />
                <span style={{ fontSize: '12px' }}>
                  {formData.image ? 'IMAGE SELECTED' : 'DRAG_EVIDENCE_IMG OR CLICK'}
                </span>
                {formData.image && (
                  <span className="selected-file-name">{formData.image.name}</span>
                )}
              </div>
            </label>

            {/* Description Input */}
            <div className="form-group">
              <label className="form-label">OBSERVATION_LOG</label>
              <textarea
                className="form-input"
                rows="2"
                placeholder="Describe current status..."
                value={formData.description}
                onChange={handleDescriptionChange}
              />
            </div>

            <button type="submit" className="btn-verify" disabled={!formData.image}>
              <Scan size={18} />
              INITIATE_VERIFICATION_PROTOCOL
            </button>
          </form>
        )}

        {/* AI Processing Visualization */}
        {isVerifying && (
          <div className="ai-feed">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#10b981', marginBottom: '12px' }}>
              <Activity size={14} className="spinner" />
              <span>AI_AGENT_V4 ACTIVE</span>
            </div>

            <div className={`ai-step ${step >= 1 ? 'active' : ''}`}>
              {step === 1 ? '> Scanning image visual data...' : '> Image scan complete.'}
            </div>
            <div className={`ai-step ${step >= 2 ? 'active' : ''}`}>
              {step === 2 ? '> Cross-referencing Instagram API...' : '> Social signals matched.'}
            </div>
            <div className={`ai-step ${step >= 3 ? 'done' : ''}`}>
              {step === 3 ? '> VERDICT: APPROVED. UNLOCKING FUNDS.' : ''}
            </div>
          </div>
        )}

        {/* Success State */}
        {selectedLocation.status === 'fresh' && (
          <div style={{ background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.2)', padding: '1rem', borderRadius: '8px', display: 'flex', gap: '10px', alignItems: 'center' }}>
            <CheckCircle2 color="#10b981" size={24} />
            <div>
              <div style={{ color: '#fff', fontWeight: 'bold', fontSize: '14px' }}>Data Synchronized</div>
              <div style={{ color: '#10b981', fontSize: '11px' }}>Blockchain transaction confirmed.</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// --- MAIN APP COMPONENT ---

export default function App() {
  const [locations, setLocations] = useState(LOCATIONS);
  const [selectedId, setSelectedId] = useState(null);
  const [balance, setBalance] = useState(INITIAL_BALANCE);

  // Derived state
  const selectedLocation = locations.find(l => l.id === selectedId);

  const handleVerify = (id) => {
    // Update local state to show 'Fresh'
    setLocations(prev => prev.map(loc =>
      loc.id === id ? { ...loc, status: 'fresh' } : loc
    ));
    // Add money
    setBalance(prev => prev + BOUNTY_REWARD);
  };

  return (
    <div className="app-container">

      {/* 2D HUD Overlays */}
      <DashboardHeader balance={balance} />

      <div className="live-feed">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', color: 'white' }}>
          <Search size={14} />
          <span>LIVE_FEED</span>
        </div>
        <div className="feed-item">> Node #8492 verified "Pizza Express"</div>
        <div className="feed-item">> New bounty added: "Cowley Cinema" ($4.20)</div>
        <div className="feed-item">> System latency: 12ms</div>
      </div>

      <BountyPanel
        selectedLocation={selectedLocation}
        onClose={() => setSelectedId(null)}
        onVerify={handleVerify}
      />

      {/* 3D Scene */}
      <Canvas shadows dpr={[1, 2]}>
        {/* Camera */}
        <PerspectiveCamera makeDefault position={[6, 5, 8]} fov={45} />
        <OrbitControls
          enablePan={false}
          minPolarAngle={0}
          maxPolarAngle={Math.PI / 2.1} // Prevent going below floor
          autoRotate={!selectedId}
          autoRotateSpeed={0.8}
          minDistance={5}
          maxDistance={20}
        />

        {/* Environment / Lighting */}
        <color attach="background" args={['#050505']} />
        <fog attach="fog" args={['#050505', 8, 25]} />

        <ambientLight intensity={0.2} />
        <pointLight position={[10, 10, 10]} intensity={1.5} castShadow />
        <Stars radius={100} depth={50} count={5000} factor={4} saturation={0} fade speed={1} />

        {/* Objects */}
        <GridFloor />

        {locations.map(loc => (
          <DataBeacon
            key={loc.id}
            {...loc}
            isSelected={selectedId === loc.id}
            onClick={() => setSelectedId(loc.id)}
          />
        ))}

        {/* Post Processing Effects */}
        <EffectComposer disableNormalPass>
          <Bloom
            luminanceThreshold={1}
            mipmapBlur
            intensity={1.5}
            radius={0.6}
          />
          <Noise opacity={0.05} />
          <Vignette eskil={false} offset={0.1} darkness={1.1} />
        </EffectComposer>
      </Canvas>
    </div>
  );
}