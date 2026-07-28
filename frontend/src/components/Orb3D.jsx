import { useRef, useMemo, useEffect } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import * as THREE from "three";

const COLORS = {
  idle: new THREE.Color("#3a3d45"),
  listening: new THREE.Color("#4FD1C5"),
  thinking: new THREE.Color("#FF8A3D"),
  speaking: new THREE.Color("#FF8A3D"),
  confirming: new THREE.Color("#E85D4C"),
};

const STATE_SPEED = {
  idle: 0.2,
  listening: 0.6,
  thinking: 1.2,
  speaking: 0.8,
  confirming: 0.4,
};

function FacetedOrb({ agentState }) {
  const meshRef = useRef();
  const materialRef = useRef();
  const timeRef = useRef(0);
  const targetColor = useRef(COLORS.idle);
  const currentColor = useRef(COLORS.idle.clone());

  const geometry = useMemo(() => {
    const geo = new THREE.IcosahedronGeometry(1.2, 2);
    const pos = geo.attributes.position;
    for (let i = 0; i < pos.count; i++) {
      const noise = (Math.random() - 0.5) * 0.08;
      pos.setX(i, pos.getX(i) + noise);
      pos.setY(i, pos.getY(i) + noise);
      pos.setZ(i, pos.getZ(i) + noise);
    }
    geo.computeVertexNormals();
    return geo;
  }, []);

  useEffect(() => {
    targetColor.current = COLORS[agentState] || COLORS.idle;
  }, [agentState]);

  useFrame((_, delta) => {
    if (!meshRef.current || !materialRef.current) return;

    timeRef.current += delta * (STATE_SPEED[agentState] || 0.2);
    const t = timeRef.current;

    currentColor.current.lerp(targetColor.current, delta * 3);
    materialRef.current.color.copy(currentColor.current);

    let scale = 1.0;
    if (agentState === "listening") {
      scale = 1.0 + Math.sin(t * 4) * 0.04 + Math.sin(t * 7) * 0.02;
    } else if (agentState === "thinking") {
      scale = 1.0 + Math.sin(t * 8) * 0.03;
    } else if (agentState === "speaking") {
      scale = 1.0 + Math.sin(t * 6) * 0.06 + Math.sin(t * 11) * 0.03;
    } else if (agentState === "confirming") {
      scale = 1.0 + Math.sin(t * 3) * 0.05;
    } else {
      scale = 1.0 + Math.sin(t * 0.5) * 0.01;
    }
    meshRef.current.scale.setScalar(scale);

    meshRef.current.rotation.y += delta * (STATE_SPEED[agentState] || 0.1) * 0.3;
    meshRef.current.rotation.x = Math.sin(t * 0.3) * 0.1;

    const pos = geometry.attributes.position;
    const origGeo = new THREE.IcosahedronGeometry(1.2, 2);
    const origPos = origGeo.attributes.position;
    for (let i = 0; i < pos.count; i++) {
      const ox = origPos.getX(i);
      const oy = origPos.getY(i);
      const oz = origPos.getZ(i);

      let displacement = 0;
      if (agentState === "listening") {
        displacement = Math.sin(t * 5 + i * 0.5) * 0.02;
      } else if (agentState === "thinking") {
        displacement = Math.sin(t * 10 + i * 0.3) * 0.015;
      } else if (agentState === "speaking") {
        displacement = Math.sin(t * 8 + i * 0.7) * 0.035;
      } else if (agentState === "confirming") {
        displacement = Math.sin(t * 4 + i * 0.4) * 0.025;
      } else {
        displacement = Math.sin(t * 0.8 + i * 0.2) * 0.005;
      }

      const len = Math.sqrt(ox * ox + oy * oy + oz * oz);
      if (len > 0) {
        pos.setX(i, ox + (ox / len) * displacement);
        pos.setY(i, oy + (oy / len) * displacement);
        pos.setZ(i, oz + (oz / len) * displacement);
      }
    }
    pos.needsUpdate = true;
    geometry.computeVertexNormals();

    origGeo.dispose();
  });

  return (
    <mesh ref={meshRef} geometry={geometry}>
      <meshStandardMaterial
        ref={materialRef}
        color={COLORS.idle}
        roughness={0.6}
        metalness={0.3}
        flatShading
      />
    </mesh>
  );
}

function ParticleField({ agentState }) {
  const pointsRef = useRef();
  const count = 200;

  const { positions, speeds } = useMemo(() => {
    const pos = new Float32Array(count * 3);
    const spd = new Float32Array(count);
    for (let i = 0; i < count; i++) {
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      const r = 1.8 + Math.random() * 1.5;
      pos[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      pos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      pos[i * 3 + 2] = r * Math.cos(phi);
      spd[i] = 0.2 + Math.random() * 0.8;
    }
    return { positions: pos, speeds: spd };
  }, []);

  useFrame((_, delta) => {
    if (!pointsRef.current) return;
    const pos = pointsRef.current.geometry.attributes.position;
    const speedMul = STATE_SPEED[agentState] || 0.2;

    for (let i = 0; i < count; i++) {
      const ix = i * 3;
      const angle = Math.atan2(pos.getY(ix + 1), pos.getX(ix));
      const speed = speeds[i] * speedMul * delta;
      const cos = Math.cos(speed);
      const sin = Math.sin(speed);
      const x = pos.getX(ix);
      const y = pos.getY(ix + 1);
      pos.setX(ix, x * cos - y * sin);
      pos.setY(ix + 1, x * sin + y * cos);
    }
    pos.needsUpdate = true;
  });

  let color = "#FF8A3D";
  if (agentState === "confirming") color = "#E85D4C";
  else if (agentState === "listening") color = "#4FD1C5";
  const opacity = agentState === "idle" ? 0.15 : 0.35;

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={count}
          array={positions}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial
        color={color}
        size={0.02}
        transparent
        opacity={opacity}
        sizeAttenuation
      />
    </points>
  );
}

function GlowRing({ agentState }) {
  const ringRef = useRef();

  useFrame((_, delta) => {
    if (!ringRef.current) return;
    ringRef.current.rotation.z += delta * 0.1;
    const scale = agentState === "idle" ? 0.8 : 1.0 + Math.sin(Date.now() * 0.003) * 0.1;
    ringRef.current.scale.setScalar(scale);
  });

  let color = "#FF8A3D";
  if (agentState === "confirming") color = "#E85D4C";
  else if (agentState === "listening") color = "#4FD1C5";
  const opacity = agentState === "idle" ? 0.05 : 0.12;

  return (
    <mesh ref={ringRef} rotation={[Math.PI / 2, 0, 0]}>
      <torusGeometry args={[1.8, 0.008, 8, 64]} />
      <meshBasicMaterial color={color} transparent opacity={opacity} />
    </mesh>
  );
}

function Scene({ agentState }) {
  let lightColor = "#FF8A3D";
  if (agentState === "listening") lightColor = "#4FD1C5";
  else if (agentState === "confirming") lightColor = "#E85D4C";
  else if (agentState === "idle") lightColor = "#3a3d45";

  return (
    <>
      <ambientLight intensity={0.3} />
      <directionalLight position={[5, 5, 5]} intensity={0.8} color="#E8E6E1" />
      <pointLight position={[-3, 2, -3]} intensity={0.4} color={lightColor} />
      <FacetedOrb agentState={agentState} />
      <ParticleField agentState={agentState} />
      <GlowRing agentState={agentState} />
    </>
  );
}

export default function Orb3D({ agentState = "idle" }) {
  return (
    <div style={{ width: "100%", height: "100%", position: "absolute", inset: 0 }}>
      <Canvas
        camera={{ position: [0, 0, 4], fov: 50 }}
        style={{ background: "transparent" }}
        gl={{ antialias: true, alpha: true }}
      >
        <Scene agentState={agentState} />
      </Canvas>
    </div>
  );
}
