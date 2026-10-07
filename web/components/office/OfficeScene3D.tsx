"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import {
  ContactShadows,
  Environment,
  Float,
  Html,
  OrbitControls,
  RoundedBox,
} from "@react-three/drei";
import { useMemo, useRef } from "react";
import * as THREE from "three";
import {
  AgentView,
  DESKS,
  Desk,
  DeskId,
  STAFF,
  SPOTS,
  StaffMember,
  StaffView,
  floorStaff,
  targetForAgent,
  targetForStaff,
} from "./agentLogic";

/** Warm loft palette — charcoal + amber wood + moss glass, not flat cream. */
const C = {
  floor: "#8f7358",
  plank: "#7d6349",
  wall: "#d9cfc0",
  wallTrim: "#2a2622",
  desk: "#5c4030",
  deskTop: "#a67c52",
  metal: "#3a342e",
  glass: "#7eb8c9",
  neon: "#e8a54b",
  moss: "#3f6212",
  oxide: "#9a3412",
  fog: "#b8a890",
};

function Monitor({
  mode,
}: {
  mode: "off" | "idle" | "working" | "waiting" | "blocked";
}) {
  const lines = useRef<THREE.Group>(null);
  const glow = useRef<THREE.MeshStandardMaterial>(null);
  useFrame((state) => {
    if (lines.current) {
      const scroll = mode === "working" ? state.clock.elapsedTime * 0.08 : state.clock.elapsedTime * 0.02;
      lines.current.position.y = ((scroll % 0.12) - 0.06) * (mode === "off" ? 0 : 1);
    }
    if (glow.current) {
      const pulse =
        mode === "working"
          ? 0.55 + Math.sin(state.clock.elapsedTime * 2.2) * 0.08
          : mode === "waiting"
            ? 0.28 + Math.sin(state.clock.elapsedTime * 1.1) * 0.05
            : mode === "blocked"
              ? 0.35 + Math.sin(state.clock.elapsedTime * 3.5) * 0.12
              : mode === "idle"
                ? 0.18
                : 0;
      glow.current.emissiveIntensity = pulse;
    }
  });
  const tint =
    mode === "working"
      ? "#1e3a2f"
      : mode === "waiting"
        ? "#3a2e1a"
        : mode === "blocked"
          ? "#3a1e1a"
          : mode === "idle"
            ? "#1a2430"
            : "#0c0b0a";
  const emissive =
    mode === "working"
      ? "#3d7a52"
      : mode === "waiting"
        ? "#b45309"
        : mode === "blocked"
          ? "#9a3412"
          : mode === "idle"
            ? "#3a5a70"
            : "#000000";
  const lineColor =
    mode === "working" ? "#8fce9a" : mode === "waiting" ? "#e8b86d" : mode === "blocked" ? "#e07a6a" : "#6a8a9a";

  return (
    <group position={[-0.32, 0.78, -0.18]}>
      <mesh castShadow position={[0, 0.3, 0]}>
        <boxGeometry args={[0.58, 0.4, 0.05]} />
        <meshStandardMaterial color="#1a1614" roughness={0.35} metalness={0.45} />
      </mesh>
      {/* Bezel */}
      <mesh position={[0, 0.3, 0.026]}>
        <planeGeometry args={[0.52, 0.34]} />
        <meshStandardMaterial color="#0e0d0c" roughness={0.4} />
      </mesh>
      <mesh position={[0, 0.3, 0.028]}>
        <planeGeometry args={[0.48, 0.3]} />
        <meshStandardMaterial
          ref={glow}
          color={tint}
          emissive={emissive}
          emissiveIntensity={mode === "off" ? 0 : 0.4}
          roughness={0.35}
        />
      </mesh>
      {mode !== "off" ? (
        <group ref={lines} position={[0, 0.3, 0.031]}>
          {[0.1, 0.06, 0.02, -0.02, -0.06, -0.1].map((y, i) => (
            <mesh key={i} position={[-0.06 + (i % 3) * 0.02, y, 0]}>
              <planeGeometry args={[0.28 - (i % 4) * 0.04, 0.012]} />
              <meshBasicMaterial color={lineColor} transparent opacity={0.55 + (i % 3) * 0.1} />
            </mesh>
          ))}
          {/* sidebar */}
          <mesh position={[-0.18, 0, 0]}>
            <planeGeometry args={[0.06, 0.26]} />
            <meshBasicMaterial color="#0a1210" transparent opacity={0.7} />
          </mesh>
          {/* cursor blink */}
          <mesh position={[0.12, 0.04, 0.001]}>
            <planeGeometry args={[0.01, 0.035]} />
            <meshBasicMaterial color="#e8f5e0" transparent opacity={0.85} />
          </mesh>
        </group>
      ) : null}
      <mesh position={[0, 0.06, 0.02]} castShadow>
        <cylinderGeometry args={[0.04, 0.07, 0.1, 12]} />
        <meshStandardMaterial color="#2a2420" metalness={0.3} roughness={0.5} />
      </mesh>
      <mesh position={[0, 0.01, 0.05]} castShadow>
        <boxGeometry args={[0.18, 0.02, 0.12]} />
        <meshStandardMaterial color="#1c1915" />
      </mesh>
    </group>
  );
}

function OpenLaptop({ lit }: { lit: boolean }) {
  return (
    <group position={[0.15, 0.78, 0]} rotation={[0, -0.25, 0]}>
      <mesh castShadow>
        <boxGeometry args={[0.38, 0.015, 0.26]} />
        <meshStandardMaterial color="#1c1915" metalness={0.45} roughness={0.4} />
      </mesh>
      <mesh position={[0, 0.14, -0.11]} rotation={[0.55, 0, 0]} castShadow>
        <boxGeometry args={[0.38, 0.24, 0.012]} />
        <meshStandardMaterial color="#22201e" metalness={0.4} roughness={0.35} />
      </mesh>
      <mesh position={[0, 0.14, -0.1]} rotation={[0.55, 0, 0]}>
        <planeGeometry args={[0.34, 0.2]} />
        <meshStandardMaterial
          color={lit ? "#1a2e3a" : "#0c0b0a"}
          emissive={lit ? "#3a6a7a" : "#000"}
          emissiveIntensity={lit ? 0.55 : 0}
          roughness={0.3}
        />
      </mesh>
      {lit ? (
        <>
          <mesh position={[-0.06, 0.16, -0.095]} rotation={[0.55, 0, 0]}>
            <planeGeometry args={[0.14, 0.02]} />
            <meshBasicMaterial color="#7ab8c8" transparent opacity={0.7} />
          </mesh>
          <mesh position={[0.04, 0.12, -0.09]} rotation={[0.55, 0, 0]}>
            <planeGeometry args={[0.18, 0.015]} />
            <meshBasicMaterial color="#5a98a8" transparent opacity={0.55} />
          </mesh>
          <pointLight position={[0, 0.2, 0.05]} intensity={0.25} distance={1.4} color="#9ec8d4" />
        </>
      ) : null}
    </group>
  );
}

function DeskMesh({
  desk,
  mode,
}: {
  desk: Desk;
  mode: "off" | "idle" | "working" | "waiting" | "blocked";
}) {
  const working = mode === "working";
  return (
    <group position={[desk.x, 0, desk.z]}>
      <RoundedBox args={[1.9, 0.08, 1.1]} radius={0.025} position={[0, 0.74, 0]} castShadow receiveShadow>
        <meshStandardMaterial color={C.deskTop} roughness={0.4} metalness={0.06} />
      </RoundedBox>
      <mesh position={[0, 0.785, 0]} receiveShadow>
        <boxGeometry args={[1.86, 0.004, 1.06]} />
        <meshStandardMaterial color="#8b6540" roughness={0.85} transparent opacity={0.35} />
      </mesh>
      {[
        [-0.8, 0.37, -0.42],
        [0.8, 0.37, -0.42],
        [-0.8, 0.37, 0.42],
        [0.8, 0.37, 0.42],
      ].map((pos, i) => (
        <mesh key={i} position={pos as [number, number, number]} castShadow>
          <cylinderGeometry args={[0.045, 0.055, 0.74, 12]} />
          <meshStandardMaterial color="#2e2118" roughness={0.75} />
        </mesh>
      ))}
      <Monitor mode={mode} />
      <OpenLaptop lit={mode === "working" || mode === "waiting"} />
      {/* keyboard */}
      <mesh position={[0.05, 0.79, 0.28]} castShadow>
        <boxGeometry args={[0.42, 0.02, 0.16]} />
        <meshStandardMaterial color="#1c1915" roughness={0.6} />
      </mesh>
      <mesh position={[0.05, 0.805, 0.28]}>
        <boxGeometry args={[0.38, 0.008, 0.12]} />
        <meshStandardMaterial color="#2a2420" />
      </mesh>
      {/* mouse */}
      <mesh position={[0.42, 0.795, 0.3]} castShadow>
        <capsuleGeometry args={[0.025, 0.04, 4, 8]} />
        <meshStandardMaterial color="#2a2420" />
      </mesh>
      <RubberDuck position={[0.62, 0.82, -0.18]} />
      <mesh position={[0.5, 0.79, 0.05]} rotation={[0, -0.35, 0]} castShadow>
        <boxGeometry args={[0.22, 0.012, 0.18]} />
        <meshStandardMaterial color="#f0e6d4" roughness={0.95} />
      </mesh>
      <mesh position={[0.12, 0.79, 0.48]} castShadow>
        <boxGeometry args={[0.72, 0.025, 0.16]} />
        <meshStandardMaterial color="#1c1915" metalness={0.2} roughness={0.5} />
      </mesh>
      <Html position={[0.12, 0.98, 0.48]} center distanceFactor={9} style={{ pointerEvents: "none" }}>
        <div className="office-nameplate">
          <p className="name">{desk.label}</p>
          <p className="role">{desk.roleTitle}</p>
        </div>
      </Html>
      {/* chair */}
      <group position={[0, 0, 0.82]}>
        <mesh position={[0, 0.34, 0]} castShadow>
          <boxGeometry args={[0.5, 0.06, 0.48]} />
          <meshStandardMaterial color="#1f1a17" roughness={0.7} />
        </mesh>
        <mesh position={[0, 0.6, -0.2]} castShadow>
          <boxGeometry args={[0.5, 0.48, 0.06]} />
          <meshStandardMaterial color="#1f1a17" roughness={0.7} />
        </mesh>
        <mesh position={[0, 0.16, 0]} castShadow>
          <cylinderGeometry args={[0.05, 0.05, 0.3, 12]} />
          <meshStandardMaterial color="#141210" metalness={0.4} />
        </mesh>
        {[0, 1, 2, 3, 4].map((i) => {
          const a = (i / 5) * Math.PI * 2;
          return (
            <mesh key={i} position={[Math.cos(a) * 0.22, 0.04, Math.sin(a) * 0.22]} castShadow>
              <sphereGeometry args={[0.04, 10, 10]} />
              <meshStandardMaterial color="#1c1915" metalness={0.5} roughness={0.4} />
            </mesh>
          );
        })}
      </group>
      {working ? (
        <pointLight position={[-0.32, 1.1, -0.1]} intensity={0.28} distance={2.2} color="#9ec9a0" />
      ) : null}
    </group>
  );
}

function Steam({ active }: { active: boolean }) {
  const refs = useRef<THREE.Mesh[]>([]);
  useFrame((state) => {
    refs.current.forEach((mesh, i) => {
      if (!mesh) return;
      const t = state.clock.elapsedTime * 1.2 + i * 0.7;
      const rise = ((t % 2) / 2) * 0.55;
      mesh.position.y = 1.35 + rise;
      mesh.scale.setScalar(0.5 + rise);
      const mat = mesh.material as THREE.MeshStandardMaterial;
      mat.opacity = active ? 0.4 * (1 - rise / 0.55) : 0;
    });
  });
  return (
    <group>
      {[0, 1, 2].map((i) => (
        <mesh
          key={i}
          ref={(node) => {
            if (node) refs.current[i] = node;
          }}
          position={[0.05 * i, 1.35, 0]}
        >
          <sphereGeometry args={[0.06, 10, 10]} />
          <meshStandardMaterial color="#f5f0e6" transparent opacity={0} depthWrite={false} />
        </mesh>
      ))}
    </group>
  );
}

function CoffeeMachine({ brewing }: { brewing: boolean }) {
  return (
    <group position={[SPOTS.coffeeMachine.x, 0, SPOTS.coffeeMachine.z]}>
      <RoundedBox args={[2.0, 0.12, 0.95]} radius={0.03} position={[0, 0.95, 0]} castShadow receiveShadow>
        <meshStandardMaterial color="#3d322a" roughness={0.55} metalness={0.15} />
      </RoundedBox>
      <RoundedBox args={[1.95, 0.9, 0.9]} radius={0.02} position={[0, 0.45, 0]} castShadow>
        <meshStandardMaterial color="#2a221c" roughness={0.7} />
      </RoundedBox>
      <mesh position={[0.2, 1.35, 0]} castShadow>
        <boxGeometry args={[0.55, 0.72, 0.42]} />
        <meshStandardMaterial color="#4a4038" roughness={0.35} metalness={0.4} />
      </mesh>
      <mesh position={[0.2, 1.68, 0.14]}>
        <boxGeometry args={[0.32, 0.1, 0.06]} />
        <meshStandardMaterial
          color={brewing ? C.moss : "#1c1915"}
          emissive={brewing ? C.moss : "#000"}
          emissiveIntensity={brewing ? 0.8 : 0}
        />
      </mesh>
      <mesh position={[0.2, 1.15, 0.24]} castShadow>
        <cylinderGeometry args={[0.045, 0.045, 0.18, 12]} />
        <meshStandardMaterial color="#8a7560" metalness={0.5} roughness={0.3} />
      </mesh>
      <mesh position={[0.2, 1.05, 0.3]} castShadow>
        <cylinderGeometry args={[0.075, 0.065, 0.11, 18]} />
        <meshStandardMaterial color="#f3efe6" roughness={0.45} />
      </mesh>
      {brewing ? (
        <mesh position={[0.2, 1.12, 0.3]}>
          <cylinderGeometry args={[0.015, 0.015, 0.14, 6]} />
          <meshStandardMaterial color="#4a2c1a" emissive="#6b3b1f" emissiveIntensity={0.4} />
        </mesh>
      ) : null}
      <group position={[0.2, 0, 0]}>
        <Steam active={brewing} />
      </group>
      <mesh position={[-0.5, 1.4, 0]} castShadow>
        <cylinderGeometry args={[0.17, 0.19, 0.58, 18]} />
        <meshStandardMaterial color="#4a4036" metalness={0.3} roughness={0.4} />
      </mesh>
      <mesh position={[-0.5, 1.78, 0]} castShadow>
        <sphereGeometry args={[0.15, 18, 18]} />
        <meshStandardMaterial color="#2c241c" transparent opacity={0.5} roughness={0.15} />
      </mesh>
      {[0, 1, 2].map((i) => (
        <mesh key={i} position={[-0.85, 1.05 + i * 0.09, 0.18]} castShadow>
          <cylinderGeometry args={[0.06, 0.05, 0.08, 12]} />
          <meshStandardMaterial color="#efe6d6" />
        </mesh>
      ))}
      {/* chalk menu */}
      <mesh position={[0.85, 1.45, 0]} castShadow>
        <boxGeometry args={[0.35, 0.5, 0.04]} />
        <meshStandardMaterial color="#1c1915" />
      </mesh>
      <Html position={[0.85, 1.45, 0.05]} center distanceFactor={10} style={{ pointerEvents: "none" }}>
        <div className="office-menu-board">
          <p>POUR-OVER</p>
          <p>FLAT WHITE</p>
          <p>BUG JUICE</p>
        </div>
      </Html>
    </group>
  );
}

function WaterCooler() {
  const water = useRef<THREE.Mesh>(null);
  useFrame((state) => {
    if (!water.current) return;
    const mat = water.current.material as THREE.MeshStandardMaterial;
    mat.emissiveIntensity = 0.12 + Math.sin(state.clock.elapsedTime * 2) * 0.04;
  });
  return (
    <group position={[SPOTS.waterCooler.x, 0, SPOTS.waterCooler.z]}>
      <mesh position={[0, 0.55, 0]} castShadow>
        <boxGeometry args={[0.55, 1.1, 0.45]} />
        <meshStandardMaterial color="#cfc8ba" roughness={0.45} metalness={0.2} />
      </mesh>
      <mesh ref={water} position={[0, 1.38, 0]} castShadow>
        <sphereGeometry args={[0.3, 24, 24]} />
        <meshStandardMaterial
          color="#7eb8c9"
          emissive="#4a90a4"
          emissiveIntensity={0.15}
          transparent
          opacity={0.55}
          roughness={0.1}
        />
      </mesh>
      <mesh position={[0.14, 0.88, 0.24]}>
        <boxGeometry args={[0.08, 0.06, 0.1]} />
        <meshStandardMaterial color="#5a5248" metalness={0.4} />
      </mesh>
    </group>
  );
}

function SnackShelf() {
  return (
    <group position={[SPOTS.snack.x, 0, SPOTS.snack.z]}>
      <mesh position={[0, 0.9, 0]} castShadow>
        <boxGeometry args={[0.72, 1.65, 0.38]} />
        <meshStandardMaterial color="#4a3428" roughness={0.75} />
      </mesh>
      {[0.35, 0.8, 1.25].map((y, i) => (
        <mesh key={i} position={[0, y, 0.06]}>
          <boxGeometry args={[0.62, 0.04, 0.3]} />
          <meshStandardMaterial color="#6b4a32" />
        </mesh>
      ))}
      {[0, 1, 2, 3].map((i) => (
        <mesh key={i} position={[-0.2 + (i % 3) * 0.16, 0.95 + Math.floor(i / 3) * 0.2, 0.12]} castShadow>
          <boxGeometry args={[0.1, 0.15, 0.08]} />
          <meshStandardMaterial color={i % 2 ? C.oxide : "#c4a574"} />
        </mesh>
      ))}
    </group>
  );
}

function Whiteboard() {
  return (
    <group position={[-5.35, 1.5, -5.28]}>
      <mesh castShadow>
        <boxGeometry args={[2.35, 1.45, 0.08]} />
        <meshStandardMaterial color="#2a2622" roughness={0.6} />
      </mesh>
      <mesh position={[0, 0, 0.05]}>
        <planeGeometry args={[2.15, 1.25]} />
        <meshStandardMaterial color="#f7f2e8" roughness={0.3} />
      </mesh>
      <mesh position={[-0.35, 0.2, 0.06]} rotation={[0, 0, -0.12]}>
        <boxGeometry args={[0.95, 0.035, 0.01]} />
        <meshStandardMaterial color={C.oxide} />
      </mesh>
      <mesh position={[0.25, -0.05, 0.06]}>
        <boxGeometry args={[0.75, 0.03, 0.01]} />
        <meshStandardMaterial color={C.moss} />
      </mesh>
      <mesh position={[0.05, 0.4, 0.06]} rotation={[0, 0, 0.1]}>
        <boxGeometry args={[1.2, 0.028, 0.01]} />
        <meshStandardMaterial color="#2f4458" />
      </mesh>
      {/* sticky notes */}
      {[
        [-0.7, -0.35, "#f0c27a"],
        [-0.4, -0.4, "#cfe8b8"],
        [0.55, 0.15, "#f5c6c6"],
      ].map(([x, y, color], i) => (
        <mesh key={i} position={[x as number, y as number, 0.065]}>
          <planeGeometry args={[0.18, 0.18]} />
          <meshStandardMaterial color={color as string} />
        </mesh>
      ))}
    </group>
  );
}

function NeonSign() {
  const glow = useRef<THREE.PointLight>(null);
  useFrame((state) => {
    if (!glow.current) return;
    glow.current.intensity = 0.55 + Math.sin(state.clock.elapsedTime * 3.2) * 0.12;
  });
  return (
    <Float speed={1.2} rotationIntensity={0.05} floatIntensity={0.15}>
      <group position={[3.2, 2.2, -5.3]}>
        <mesh castShadow>
          <boxGeometry args={[3.4, 0.55, 0.08]} />
          <meshStandardMaterial color="#1a1614" roughness={0.5} metalness={0.2} />
        </mesh>
        <Html position={[0, 0, 0.06]} center distanceFactor={12} style={{ pointerEvents: "none" }}>
          <div className="office-neon">CODERS ALLEY</div>
        </Html>
        <pointLight ref={glow} position={[0, 0, 0.4]} color={C.neon} distance={5} intensity={0.6} />
        <mesh position={[0, 0, 0.05]}>
          <planeGeometry args={[3.1, 0.35]} />
          <meshStandardMaterial
            color={C.neon}
            emissive={C.neon}
            emissiveIntensity={0.7}
            transparent
            opacity={0.25}
          />
        </mesh>
      </group>
    </Float>
  );
}

function FoosballTable({ spinning }: { spinning: boolean }) {
  const rods = useRef<THREE.Group>(null);
  useFrame((state) => {
    if (!rods.current) return;
    rods.current.rotation.x = spinning
      ? state.clock.elapsedTime * 3.5
      : Math.sin(state.clock.elapsedTime * 0.6) * 0.15;
  });
  const midX = (SPOTS.foosball.x + SPOTS.foosballB.x) / 2;
  const midZ = (SPOTS.foosball.z + SPOTS.foosballB.z) / 2;
  return (
    <group position={[midX, 0, midZ]}>
      {/* Floor pad so the game corner reads clearly */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.012, 0]} receiveShadow>
        <planeGeometry args={[2.6, 2.0]} />
        <meshStandardMaterial color="#3a4a3e" roughness={0.92} />
      </mesh>
      <RoundedBox args={[1.85, 0.14, 1.05]} radius={0.025} position={[0, 0.72, 0]} castShadow>
        <meshStandardMaterial color="#2d4a32" roughness={0.5} />
      </RoundedBox>
      <mesh position={[0, 0.8, 0]}>
        <boxGeometry args={[1.65, 0.02, 0.88]} />
        <meshStandardMaterial color="#1a3324" />
      </mesh>
      {/* Center line */}
      <mesh position={[0, 0.82, 0]}>
        <boxGeometry args={[0.02, 0.01, 0.8]} />
        <meshStandardMaterial color="#f3efe6" />
      </mesh>
      {/* goals */}
      {[-0.9, 0.9].map((x) => (
        <mesh key={x} position={[x, 0.88, 0]}>
          <boxGeometry args={[0.08, 0.2, 0.35]} />
          <meshStandardMaterial color="#f3efe6" />
        </mesh>
      ))}
      {[
        [-0.78, 0.36, -0.42],
        [0.78, 0.36, -0.42],
        [-0.78, 0.36, 0.42],
        [0.78, 0.36, 0.42],
      ].map((pos, i) => (
        <mesh key={i} position={pos as [number, number, number]} castShadow>
          <cylinderGeometry args={[0.04, 0.04, 0.72, 8]} />
          <meshStandardMaterial color="#2a2420" />
        </mesh>
      ))}
      <group ref={rods} position={[0, 0.88, 0]}>
        {[-0.35, 0, 0.35].map((z, i) => (
          <group key={i} position={[0, 0, z]}>
            <mesh rotation={[0, 0, Math.PI / 2]}>
              <cylinderGeometry args={[0.02, 0.02, 1.55, 8]} />
              <meshStandardMaterial color="#c4a574" metalness={0.5} />
            </mesh>
            {[-0.35, 0.35].map((x) => (
              <mesh key={x} position={[x, -0.08, 0]} castShadow>
                <boxGeometry args={[0.06, 0.14, 0.04]} />
                <meshStandardMaterial color={i === 1 ? C.oxide : "#f3efe6"} />
              </mesh>
            ))}
          </group>
        ))}
      </group>
      <mesh position={[0, 0.84, 0]}>
        <sphereGeometry args={[0.055, 14, 14]} />
        <meshStandardMaterial color="#f3efe6" />
      </mesh>
    </group>
  );
}

function Microwave({ hot }: { hot: boolean }) {
  return (
    <group position={[SPOTS.microwave.x, 0, SPOTS.microwave.z]}>
      <mesh position={[0, 0.55, 0]} castShadow>
        <boxGeometry args={[0.72, 1.1, 0.48]} />
        <meshStandardMaterial color="#3a322c" roughness={0.65} />
      </mesh>
      <mesh position={[0, 1.28, 0]} castShadow>
        <boxGeometry args={[0.66, 0.42, 0.42]} />
        <meshStandardMaterial color="#24201c" metalness={0.4} roughness={0.3} />
      </mesh>
      <mesh position={[0, 1.28, 0.22]}>
        <planeGeometry args={[0.48, 0.3]} />
        <meshStandardMaterial
          color={hot ? "#f0c27a" : "#12100e"}
          emissive={hot ? "#f0c27a" : "#000"}
          emissiveIntensity={hot ? 0.7 : 0}
        />
      </mesh>
      {hot ? <pointLight position={[0, 1.28, 0.35]} intensity={0.5} distance={2} color="#f0c27a" /> : null}
    </group>
  );
}

function Beanbag() {
  return (
    <group position={[SPOTS.beanbag.x, 0, SPOTS.beanbag.z]}>
      <mesh position={[0, 0.28, 0]} castShadow scale={[1.15, 0.72, 1.15]}>
        <sphereGeometry args={[0.55, 24, 24]} />
        <meshStandardMaterial color="#7a2e24" roughness={0.92} />
      </mesh>
      <mesh position={[0, 0.42, 0.1]} castShadow scale={[0.85, 0.35, 0.85]}>
        <sphereGeometry args={[0.4, 20, 20]} />
        <meshStandardMaterial color="#8f3a2e" roughness={0.95} />
      </mesh>
      <mesh position={[-1.15, 0.55, 0.15]} castShadow>
        <boxGeometry args={[0.7, 1.1, 0.25]} />
        <meshStandardMaterial color="#4a3428" />
      </mesh>
      {[0.2, 0.55, 0.9].map((y, i) => (
        <mesh key={i} position={[-1.15, y, 0.08]}>
          <boxGeometry args={[0.55, 0.04, 0.2]} />
          <meshStandardMaterial color="#6b4a32" />
        </mesh>
      ))}
      <mesh position={[-1.15, 0.78, 0.16]} castShadow>
        <boxGeometry args={[0.3, 0.1, 0.22]} />
        <meshStandardMaterial color="#efe6d6" />
      </mesh>
    </group>
  );
}

function RubberDuck({ position }: { position: [number, number, number] }) {
  return (
    <group position={position}>
      <mesh castShadow>
        <sphereGeometry args={[0.065, 14, 14]} />
        <meshStandardMaterial color="#e6b422" roughness={0.4} />
      </mesh>
      <mesh position={[0.055, 0.045, 0]} castShadow>
        <sphereGeometry args={[0.038, 12, 12]} />
        <meshStandardMaterial color="#e6b422" />
      </mesh>
      <mesh position={[0.09, 0.045, 0]} rotation={[0, 0, -Math.PI / 2]}>
        <coneGeometry args={[0.016, 0.04, 8]} />
        <meshStandardMaterial color={C.oxide} />
      </mesh>
      <mesh position={[0.06, 0.055, 0.025]}>
        <sphereGeometry args={[0.008, 6, 6]} />
        <meshStandardMaterial color="#1c1915" />
      </mesh>
    </group>
  );
}

function SmokePatio() {
  return (
    <group position={[SPOTS.smoke.x - 0.4, 0, SPOTS.smoke.z + 0.2]}>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.02, 0]} receiveShadow>
        <planeGeometry args={[2.5, 1.9]} />
        <meshStandardMaterial color="#8a7b68" roughness={0.95} />
      </mesh>
      <mesh position={[1.15, 0.75, -0.7]} castShadow>
        <boxGeometry args={[0.1, 1.5, 1.7]} />
        <meshStandardMaterial color="#5a5248" roughness={0.7} metalness={0.15} />
      </mesh>
      <mesh position={[-0.3, 0.45, 0.1]} castShadow>
        <cylinderGeometry args={[0.04, 0.05, 0.9, 10]} />
        <meshStandardMaterial color="#3a342e" metalness={0.35} roughness={0.4} />
      </mesh>
      <mesh position={[-0.3, 0.95, 0.1]} castShadow>
        <cylinderGeometry args={[0.17, 0.15, 0.08, 16]} />
        <meshStandardMaterial color="#2a2420" metalness={0.4} roughness={0.35} />
      </mesh>
      {[0, 1, 2].map((i) => (
        <mesh
          key={i}
          position={[-0.35 + i * 0.05, 0.99, 0.08 + (i % 2) * 0.04]}
          rotation={[0.2, 0.4 * i, 0.3]}
        >
          <cylinderGeometry args={[0.012, 0.012, 0.05, 6]} />
          <meshStandardMaterial color={i === 1 ? "#f3efe6" : "#4a2c1a"} />
        </mesh>
      ))}
      <mesh position={[0.55, 0.32, 0.35]} castShadow>
        <boxGeometry args={[0.95, 0.08, 0.38]} />
        <meshStandardMaterial color="#5c4030" roughness={0.75} />
      </mesh>
      <mesh position={[0.25, 0.16, 0.35]} castShadow>
        <boxGeometry args={[0.06, 0.32, 0.06]} />
        <meshStandardMaterial color="#3a2a1c" />
      </mesh>
      <mesh position={[0.85, 0.16, 0.35]} castShadow>
        <boxGeometry args={[0.06, 0.32, 0.06]} />
        <meshStandardMaterial color="#3a2a1c" />
      </mesh>
    </group>
  );
}

function CigarettePuffs({ active }: { active: boolean }) {
  const refs = useRef<THREE.Mesh[]>([]);
  useFrame((state) => {
    refs.current.forEach((mesh, i) => {
      if (!mesh) return;
      const t = state.clock.elapsedTime * 1.4 + i * 0.55;
      const rise = ((t % 1.8) / 1.8) * 0.45;
      const drift = Math.sin(t * 1.3 + i) * 0.08;
      mesh.position.set(0.32 + drift, 1.15 + rise, 0.18);
      mesh.scale.setScalar(0.35 + rise * 1.4);
      const mat = mesh.material as THREE.MeshStandardMaterial;
      mat.opacity = active ? 0.4 * (1 - rise / 0.45) : 0;
    });
  });
  return (
    <group>
      {[0, 1, 2, 3].map((i) => (
        <mesh
          key={i}
          ref={(node) => {
            if (node) refs.current[i] = node;
          }}
        >
          <sphereGeometry args={[0.05, 8, 8]} />
          <meshStandardMaterial color="#d8d0c4" transparent opacity={0} depthWrite={false} />
        </mesh>
      ))}
    </group>
  );
}

function PaperPlane({ flying }: { flying: boolean }) {
  const ref = useRef<THREE.Group>(null);
  useFrame((state) => {
    if (!ref.current) return;
    if (!flying) {
      ref.current.visible = false;
      return;
    }
    ref.current.visible = true;
    const t = (state.clock.elapsedTime % 6) / 6;
    const x = -3 + t * 8;
    const z = -1 + Math.sin(t * Math.PI * 2) * 1.5;
    const y = 1.2 + Math.sin(t * Math.PI) * 0.6;
    ref.current.position.set(x, y, z);
    ref.current.rotation.set(0.2, -0.8 + t, Math.sin(t * 20) * 0.2);
  });
  return (
    <group ref={ref}>
      <mesh castShadow>
        <coneGeometry args={[0.08, 0.35, 3]} />
        <meshStandardMaterial color="#f3efe6" roughness={0.65} side={THREE.DoubleSide} />
      </mesh>
    </group>
  );
}

function DustMotes() {
  const points = useRef<THREE.Points>(null);
  const geometry = useMemo(() => {
    const arr = new Float32Array(80 * 3);
    for (let i = 0; i < 80; i++) {
      arr[i * 3] = (Math.random() - 0.5) * 14;
      arr[i * 3 + 1] = 0.4 + Math.random() * 2.4;
      arr[i * 3 + 2] = (Math.random() - 0.5) * 10;
    }
    const geom = new THREE.BufferGeometry();
    geom.setAttribute("position", new THREE.BufferAttribute(arr, 3));
    return geom;
  }, []);
  useFrame((state) => {
    if (!points.current) return;
    points.current.rotation.y = state.clock.elapsedTime * 0.02;
    points.current.position.y = Math.sin(state.clock.elapsedTime * 0.3) * 0.05;
  });
  return (
    <points ref={points} geometry={geometry}>
      <pointsMaterial color="#fff6e0" size={0.035} transparent opacity={0.35} depthWrite={false} sizeAttenuation />
    </points>
  );
}

function Pendant({ position }: { position: [number, number, number] }) {
  return (
    <group position={position}>
      <mesh position={[0, 0.15, 0]}>
        <cylinderGeometry args={[0.015, 0.015, 0.35, 8]} />
        <meshStandardMaterial color="#2a2420" metalness={0.4} />
      </mesh>
      <mesh>
        <sphereGeometry args={[0.14, 16, 16]} />
        <meshStandardMaterial
          color="#f5efe0"
          emissive="#fff1d0"
          emissiveIntensity={0.55}
          transparent
          opacity={0.85}
          roughness={0.2}
        />
      </mesh>
      <pointLight intensity={0.55} distance={4.5} color="#ffe8c0" />
    </group>
  );
}

function WindowBank() {
  return (
    <group>
      {[-4.6, -1.55, 1.5, 4.55].map((x, wi) => (
        <group key={x} position={[x, 1.65, -5.35]}>
          <mesh castShadow>
            <boxGeometry args={[2.2, 1.5, 0.1]} />
            <meshStandardMaterial color="#3a342e" roughness={0.55} metalness={0.15} />
          </mesh>
          <mesh position={[0, 0, 0.06]}>
            <planeGeometry args={[1.95, 1.25]} />
            <meshStandardMaterial
              color={C.glass}
              emissive="#dceaf2"
              emissiveIntensity={0.5 + wi * 0.02}
              roughness={0.08}
              metalness={0.1}
            />
          </mesh>
          <mesh position={[0, 0, 0.07]}>
            <boxGeometry args={[0.04, 1.25, 0.02]} />
            <meshStandardMaterial color="#4a4036" />
          </mesh>
          <mesh position={[0, 0, 0.07]}>
            <boxGeometry args={[1.95, 0.04, 0.02]} />
            <meshStandardMaterial color="#4a4036" />
          </mesh>
          <mesh position={[0, -0.95, 1.3]} rotation={[0.55, 0, 0]}>
            <planeGeometry args={[1.6, 2.5]} />
            <meshBasicMaterial color="#fff4d8" transparent opacity={0.07} depthWrite={false} side={THREE.DoubleSide} />
          </mesh>
        </group>
      ))}
    </group>
  );
}

function ReceptionDesk() {
  return (
    <group position={[SPOTS.reception.x, 0, SPOTS.reception.z]}>
      <RoundedBox args={[1.6, 0.12, 0.7]} radius={0.03} position={[0, 0.92, 0]} castShadow receiveShadow>
        <meshStandardMaterial color="#6b4e35" roughness={0.5} />
      </RoundedBox>
      <RoundedBox args={[1.55, 0.85, 0.55]} radius={0.02} position={[0, 0.42, 0.05]} castShadow>
        <meshStandardMaterial color="#3d3228" roughness={0.75} />
      </RoundedBox>
      {/* Counter front panel */}
      <mesh position={[0, 0.45, 0.36]} castShadow>
        <boxGeometry args={[1.55, 0.9, 0.04]} />
        <meshStandardMaterial color="#2a2118" roughness={0.7} />
      </mesh>
      <mesh position={[0, 0.7, 0.385]}>
        <planeGeometry args={[0.7, 0.18]} />
        <meshStandardMaterial color="#efe6d6" />
      </mesh>
      <Html position={[0, 1.35, 0.2]} center distanceFactor={10} style={{ pointerEvents: "none" }}>
        <div className="office-nameplate">
          <p className="name">Reception</p>
          <p className="role">Coders Alley</p>
        </div>
      </Html>
      {/* Guest chair */}
      <group position={[0.15, 0, 0.95]}>
        <mesh position={[0, 0.32, 0]} castShadow>
          <boxGeometry args={[0.4, 0.05, 0.38]} />
          <meshStandardMaterial color="#3a322c" />
        </mesh>
        <mesh position={[0, 0.5, -0.14]} castShadow>
          <boxGeometry args={[0.4, 0.32, 0.05]} />
          <meshStandardMaterial color="#3a322c" />
        </mesh>
      </group>
      <group position={[0.25, 0.14, -0.05]}>
        <OpenLaptop lit />
      </group>
      <mesh position={[-0.45, 0.99, 0.05]} castShadow>
        <cylinderGeometry args={[0.06, 0.05, 0.12, 12]} />
        <meshStandardMaterial color="#f3efe6" />
      </mesh>
      <pointLight position={[0, 1.4, 0.3]} intensity={0.25} distance={2.5} color="#ffe8c0" />
    </group>
  );
}

/** Extra set dressing so the floor reads as a real office, not empty props. */
function ExtraFurniture() {
  return (
    <group>
      <ReceptionDesk />
      {/* Lounge sofa */}
      <group position={[-5.2, 0, 0.6]}>
        <RoundedBox args={[2.2, 0.35, 0.85]} radius={0.06} position={[0, 0.28, 0]} castShadow>
          <meshStandardMaterial color="#3d4a52" roughness={0.85} />
        </RoundedBox>
        <RoundedBox args={[2.2, 0.45, 0.18]} radius={0.04} position={[0, 0.55, -0.32]} castShadow>
          <meshStandardMaterial color="#324048" roughness={0.85} />
        </RoundedBox>
        {[-0.95, 0.95].map((x) => (
          <RoundedBox key={x} args={[0.18, 0.4, 0.85]} radius={0.04} position={[x, 0.45, 0]} castShadow>
            <meshStandardMaterial color="#324048" roughness={0.85} />
          </RoundedBox>
        ))}
        <mesh position={[0, 0.12, 0.55]} castShadow>
          <cylinderGeometry args={[0.28, 0.3, 0.08, 20]} />
          <meshStandardMaterial color="#5c4030" roughness={0.7} />
        </mesh>
        <mesh position={[0, 0.2, 0.55]} castShadow>
          <boxGeometry args={[0.35, 0.04, 0.25]} />
          <meshStandardMaterial color="#efe6d6" />
        </mesh>
      </group>

      {/* Meeting table + chairs */}
      <group position={[0.2, 0, 2.2]}>
        <RoundedBox args={[2.4, 0.08, 1.1]} radius={0.03} position={[0, 0.72, 0]} castShadow receiveShadow>
          <meshStandardMaterial color="#6b4e35" roughness={0.45} />
        </RoundedBox>
        {[
          [-0.9, 0.36, -0.4],
          [0.9, 0.36, -0.4],
          [-0.9, 0.36, 0.4],
          [0.9, 0.36, 0.4],
        ].map((pos, i) => (
          <mesh key={i} position={pos as [number, number, number]} castShadow>
            <cylinderGeometry args={[0.05, 0.06, 0.72, 10]} />
            <meshStandardMaterial color="#2e2118" />
          </mesh>
        ))}
        {[-0.7, 0.7].map((x) => (
          <group key={x} position={[x, 0, 0.85]}>
            <mesh position={[0, 0.35, 0]} castShadow>
              <boxGeometry args={[0.42, 0.05, 0.4]} />
              <meshStandardMaterial color="#2a2420" />
            </mesh>
            <mesh position={[0, 0.55, -0.16]} castShadow>
              <boxGeometry args={[0.42, 0.35, 0.05]} />
              <meshStandardMaterial color="#2a2420" />
            </mesh>
          </group>
        ))}
        {[-0.7, 0.7].map((x) => (
          <group key={`n${x}`} position={[x, 0, -0.85]} rotation={[0, Math.PI, 0]}>
            <mesh position={[0, 0.35, 0]} castShadow>
              <boxGeometry args={[0.42, 0.05, 0.4]} />
              <meshStandardMaterial color="#2a2420" />
            </mesh>
            <mesh position={[0, 0.55, -0.16]} castShadow>
              <boxGeometry args={[0.42, 0.35, 0.05]} />
              <meshStandardMaterial color="#2a2420" />
            </mesh>
          </group>
        ))}
        <group position={[0, 0, 0]}>
          <OpenLaptop lit />
        </group>
      </group>

      {/* Bookshelf */}
      <group position={[-7.55, 0, -2.2]}>
        <mesh position={[0, 1.0, 0]} castShadow>
          <boxGeometry args={[0.35, 2.0, 1.4]} />
          <meshStandardMaterial color="#4a3428" roughness={0.8} />
        </mesh>
        {[0.35, 0.75, 1.15, 1.55].map((y) => (
          <mesh key={y} position={[0.02, y, 0]}>
            <boxGeometry args={[0.3, 0.04, 1.3]} />
            <meshStandardMaterial color="#6b4a32" />
          </mesh>
        ))}
        {Array.from({ length: 12 }).map((_, i) => (
          <mesh
            key={i}
            position={[0.08, 0.5 + (i % 4) * 0.4, -0.5 + Math.floor(i / 4) * 0.35]}
            castShadow
          >
            <boxGeometry args={[0.12, 0.28, 0.08]} />
            <meshStandardMaterial
              color={["#8b3a1a", "#2f4458", "#3f6212", "#5a4a28", "#9a3412"][i % 5]}
              roughness={0.7}
            />
          </mesh>
        ))}
      </group>

      {/* Filing cabinets */}
      {[0, 1].map((i) => (
        <group key={i} position={[6.9, 0, -2.8 + i * 0.85]}>
          <mesh position={[0, 0.55, 0]} castShadow>
            <boxGeometry args={[0.55, 1.1, 0.7]} />
            <meshStandardMaterial color="#6a6560" metalness={0.35} roughness={0.45} />
          </mesh>
          {[0.25, 0.55, 0.85].map((y) => (
            <mesh key={y} position={[0.28, y, 0]}>
              <boxGeometry args={[0.02, 0.22, 0.55]} />
              <meshStandardMaterial color="#4a4642" metalness={0.4} />
            </mesh>
          ))}
          <mesh position={[0.29, 0.55, 0.15]}>
            <boxGeometry args={[0.03, 0.04, 0.12]} />
            <meshStandardMaterial color="#c4a574" metalness={0.6} />
          </mesh>
        </group>
      ))}

      {/* Printer / copy station */}
      <group position={[6.6, 0, 0.2]}>
        <mesh position={[0, 0.4, 0]} castShadow>
          <boxGeometry args={[0.8, 0.8, 0.6]} />
          <meshStandardMaterial color="#3a3a38" metalness={0.3} roughness={0.5} />
        </mesh>
        <mesh position={[0, 0.85, 0]} castShadow>
          <boxGeometry args={[0.7, 0.25, 0.5]} />
          <meshStandardMaterial color="#2a2a28" metalness={0.4} />
        </mesh>
        <mesh position={[0, 0.85, 0.2]}>
          <planeGeometry args={[0.4, 0.12]} />
          <meshStandardMaterial color="#1c1915" emissive="#5a7a40" emissiveIntensity={0.4} />
        </mesh>
        <mesh position={[0.15, 0.98, 0]} castShadow>
          <boxGeometry args={[0.25, 0.02, 0.3]} />
          <meshStandardMaterial color="#f3efe6" />
        </mesh>
      </group>

      {/* Coat rack */}
      <group position={[-7.4, 0, 2.4]}>
        <mesh position={[0, 0.9, 0]} castShadow>
          <cylinderGeometry args={[0.04, 0.05, 1.8, 10]} />
          <meshStandardMaterial color="#2a2118" />
        </mesh>
        <mesh position={[0, 0.05, 0]} castShadow>
          <cylinderGeometry args={[0.22, 0.22, 0.04, 16]} />
          <meshStandardMaterial color="#2a2118" />
        </mesh>
        {[-0.2, 0.2].map((x, i) => (
          <mesh key={i} position={[x, 1.55, 0]} rotation={[0, 0, x > 0 ? -0.6 : 0.6]} castShadow>
            <capsuleGeometry args={[0.03, 0.35, 4, 6]} />
            <meshStandardMaterial color={i ? "#2f4458" : "#8b3a1a"} roughness={0.8} />
          </mesh>
        ))}
      </group>

      {/* Trash bins */}
      {[
        [-3.5, -4.6],
        [4.5, -4.5],
        [5.8, 3.8],
      ].map(([x, z], i) => (
        <mesh key={i} position={[x, 0.28, z]} castShadow>
          <cylinderGeometry args={[0.16, 0.14, 0.55, 14]} />
          <meshStandardMaterial color="#3a3a38" metalness={0.4} roughness={0.5} />
        </mesh>
      ))}

      {/* Low partition behind desk row */}
      <mesh position={[0.7, 0.55, -3.55]} castShadow>
        <boxGeometry args={[8.2, 1.1, 0.08]} />
        <meshStandardMaterial color="#cfc4b0" roughness={0.9} />
      </mesh>
      <mesh position={[0.7, 1.15, -3.55]}>
        <boxGeometry args={[8.2, 0.06, 0.1]} />
        <meshStandardMaterial color="#5c4a38" />
      </mesh>

      {/* Server / blinky rack (AI corner vibe) */}
      <group position={[-6.8, 0, -4.5]}>
        <mesh position={[0, 0.9, 0]} castShadow>
          <boxGeometry args={[0.7, 1.8, 0.55]} />
          <meshStandardMaterial color="#1c1915" metalness={0.45} roughness={0.4} />
        </mesh>
        {[0.3, 0.55, 0.8, 1.05, 1.3, 1.55].map((y, i) => (
          <mesh key={y} position={[0.36, y, 0]}>
            <boxGeometry args={[0.02, 0.08, 0.4]} />
            <meshStandardMaterial
              color={i % 2 ? C.moss : "#4a90a4"}
              emissive={i % 2 ? C.moss : "#4a90a4"}
              emissiveIntensity={0.6}
            />
          </mesh>
        ))}
      </group>

      {/* Floor lamp */}
      <group position={[-4.0, 0, 1.4]}>
        <mesh position={[0, 0.7, 0]} castShadow>
          <cylinderGeometry args={[0.03, 0.04, 1.4, 10]} />
          <meshStandardMaterial color="#2a2118" metalness={0.3} />
        </mesh>
        <mesh position={[0, 1.45, 0]} castShadow>
          <coneGeometry args={[0.28, 0.35, 16]} />
          <meshStandardMaterial color="#efe6d6" emissive="#fff1d0" emissiveIntensity={0.25} />
        </mesh>
        <pointLight position={[0, 1.3, 0]} intensity={0.35} distance={3.5} color="#ffe8c0" />
      </group>

      {/* Wall clock */}
      <group position={[0.5, 2.35, -5.35]}>
        <mesh>
          <cylinderGeometry args={[0.28, 0.28, 0.06, 28]} />
          <meshStandardMaterial color="#f3efe6" roughness={0.4} />
        </mesh>
        <mesh position={[0, 0, 0.04]} rotation={[Math.PI / 2, 0, 0.4]}>
          <boxGeometry args={[0.02, 0.18, 0.01]} />
          <meshStandardMaterial color="#1c1915" />
        </mesh>
      </group>

      {/* Framed posters */}
      {[
        [-2.5, "#8b3a1a"],
        [2.8, "#2f4458"],
      ].map(([x, color], i) => (
        <group key={i} position={[x as number, 2.1, -5.38]}>
          <mesh>
            <boxGeometry args={[0.7, 0.55, 0.04]} />
            <meshStandardMaterial color="#2a2118" />
          </mesh>
          <mesh position={[0, 0, 0.025]}>
            <planeGeometry args={[0.58, 0.42]} />
            <meshStandardMaterial color={color as string} />
          </mesh>
        </group>
      ))}
    </group>
  );
}

function Room({
  brewing,
  foosball,
  microwave,
}: {
  brewing: boolean;
  foosball: boolean;
  microwave: boolean;
}) {
  return (
    <group>
      {/* floor */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <planeGeometry args={[16, 12]} />
        <meshStandardMaterial color={C.floor} roughness={0.92} />
      </mesh>
      {Array.from({ length: 20 }).map((_, i) => (
        <mesh key={i} rotation={[-Math.PI / 2, 0, 0]} position={[-7.6 + i * 0.8, 0.004, 0]} receiveShadow>
          <planeGeometry args={[0.04, 12]} />
          <meshStandardMaterial color={C.plank} roughness={1} />
        </mesh>
      ))}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0.6, 0.012, -1.4]} receiveShadow>
        <planeGeometry args={[8.5, 4.2]} />
        <meshStandardMaterial color="#6b5340" roughness={1} />
      </mesh>
      {/* Lounge rug */}
      <mesh rotation={[-Math.PI / 2, 0, 0.15]} position={[-5.1, 0.013, 0.7]} receiveShadow>
        <planeGeometry args={[3.2, 2.2]} />
        <meshStandardMaterial color="#5a4030" roughness={1} />
      </mesh>

      {/* Open loft: walls only — no roof slab so the camera can see the whole floor */}
      <mesh position={[0, 1.35, -5.55]} receiveShadow>
        <boxGeometry args={[16, 2.7, 0.28]} />
        <meshStandardMaterial color={C.wall} roughness={0.95} />
      </mesh>
      <mesh position={[-7.95, 1.25, 0]} receiveShadow>
        <boxGeometry args={[0.24, 2.5, 12]} />
        <meshStandardMaterial color={C.wall} roughness={0.95} />
      </mesh>
      <mesh position={[7.95, 1.25, 0]} receiveShadow>
        <boxGeometry args={[0.24, 2.5, 12]} />
        <meshStandardMaterial color={C.wall} roughness={0.95} />
      </mesh>
      {/* wall tops / cornice hint without a blocking ceiling */}
      <mesh position={[0, 2.72, -5.55]}>
        <boxGeometry args={[16, 0.1, 0.35]} />
        <meshStandardMaterial color={C.wallTrim} roughness={0.7} />
      </mesh>
      <mesh position={[0, 0.08, -5.4]}>
        <boxGeometry args={[15.8, 0.16, 0.08]} />
        <meshStandardMaterial color={C.wallTrim} roughness={0.7} />
      </mesh>

      {/* Short edge beams only — stay clear of the center view */}
      {[-6.5, 6.5].map((x) => (
        <mesh key={x} position={[x, 2.85, -0.5]} castShadow>
          <boxGeometry args={[0.16, 0.18, 9]} />
          <meshStandardMaterial color="#5c4a38" roughness={0.8} />
        </mesh>
      ))}

      <WindowBank />
      <NeonSign />
      <Whiteboard />
      <CoffeeMachine brewing={brewing} />
      <WaterCooler />
      <SnackShelf />
      <FoosballTable spinning={foosball} />
      <Microwave hot={microwave} />
      <Beanbag />
      <SmokePatio />
      <ExtraFurniture />

      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[SPOTS.stretch.x, 0.016, SPOTS.stretch.z]} receiveShadow>
        <circleGeometry args={[1.55, 48]} />
        <meshStandardMaterial color="#7a6548" roughness={1} />
      </mesh>
      <mesh position={[SPOTS.phone.x, 0.02, SPOTS.phone.z]} rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[0.48, 28]} />
        <meshStandardMaterial color="#6a5a48" />
      </mesh>
      <mesh position={[SPOTS.phone.x, 0.95, SPOTS.phone.z - 0.35]} castShadow>
        <boxGeometry args={[0.1, 1.9, 0.1]} />
        <meshStandardMaterial color="#4a4036" metalness={0.25} />
      </mesh>
      {[
        [-6.5, -3.8],
        [6.5, -3.6],
        [SPOTS.plant.x, SPOTS.plant.z],
      ].map(([x, z], i) => (
        <group key={i} position={[x, 0, z]}>
          <mesh position={[0, 0.22, 0]} castShadow>
            <cylinderGeometry args={[0.22, 0.26, 0.44, 18]} />
            <meshStandardMaterial color="#6b4530" roughness={0.9} />
          </mesh>
          <mesh position={[0, 0.8, 0]} castShadow>
            <sphereGeometry args={[0.45, 22, 22]} />
            <meshStandardMaterial color="#3a5a1c" roughness={0.85} />
          </mesh>
          <mesh position={[0.15, 1.05, 0.1]} castShadow>
            <sphereGeometry args={[0.22, 16, 16]} />
            <meshStandardMaterial color="#4a7028" roughness={0.85} />
          </mesh>
        </group>
      ))}
      <Pendant position={[-2.2, 2.65, -1.2]} />
      <Pendant position={[2.2, 2.65, -1.2]} />
      <Pendant position={[5.2, 2.65, 2.6]} />
      <DustMotes />
    </group>
  );
}

/** Casual office walk — ~0.7 scene-units/sec, soft gait. */
const WALK_SPEED = 0.72;

function AgentMesh({
  agent,
  desk,
  index,
  funTime,
}: {
  agent: AgentView;
  desk: Desk;
  index: number;
  funTime: number;
}) {
  const group = useRef<THREE.Group>(null);
  const leftLeg = useRef<THREE.Group>(null);
  const rightLeg = useRef<THREE.Group>(null);
  const leftArm = useRef<THREE.Group>(null);
  const rightArm = useRef<THREE.Group>(null);
  const cup = useRef<THREE.Group>(null);
  const cigarette = useRef<THREE.Group>(null);
  const pos = useRef(new THREE.Vector3(desk.x, 0, desk.z + 0.7));
  const facing = useRef(Math.PI);
  const walkPhase = useRef(index * 0.7);
  const funTimeRef = useRef(funTime);
  funTimeRef.current = funTime;

  useFrame((state, delta) => {
    if (!group.current) return;
    const dt = Math.min(delta, 0.05);
    const target = targetForAgent(agent, desk, funTimeRef.current, index);
    const goal = new THREE.Vector3(target.x, 0, target.z);
    const toGoal = goal.clone().sub(pos.current);
    const dist = toGoal.length();
    const moving = dist > 0.06;

    if (moving) {
      const step = Math.min(WALK_SPEED * dt, dist);
      toGoal.normalize().multiplyScalar(step);
      pos.current.add(toGoal);
      walkPhase.current += step * 5.2;
      facing.current = Math.atan2(toGoal.x, toGoal.z);
    } else if (target.faceDesk) {
      facing.current = Math.PI;
    } else if (target.fun === "board" || target.fun === "read" || target.fun === "nap") {
      facing.current = Math.PI;
    } else if (target.fun === "brew" || target.fun === "microwave") {
      facing.current = 0;
    } else if (target.fun === "smoke") {
      facing.current = -0.55 + index * 0.12;
    } else if (target.fun === "foosball") {
      facing.current = target.z < (SPOTS.foosball.z + SPOTS.foosballB.z) / 2 ? 0 : Math.PI;
    } else if (target.fun === "phone") {
      facing.current = 0.4;
    }

    const sitY = target.sit ? (target.fun === "nap" ? 0.18 : 0.32) : 0;
    const gait = walkPhase.current;
    const walkBob = moving ? Math.sin(gait * 2) * 0.012 : 0;
    const stretch =
      target.fun === "stretch" && !moving ? Math.sin(state.clock.elapsedTime * 1.6) * 0.05 : 0;
    const celebrate =
      target.fun === "celebrate" && !moving ? Math.abs(Math.sin(state.clock.elapsedTime * 3.2)) * 0.08 : 0;
    const type =
      agent.state === "working" && !moving ? Math.sin(state.clock.elapsedTime * 7 + index) * 0.012 : 0;
    const sip =
      (target.fun === "sip" || target.fun === "phone") && !moving
        ? Math.abs(Math.sin(state.clock.elapsedTime * 1.2)) * 0.18
        : 0;
    const drag =
      target.fun === "smoke" && !moving ? Math.abs(Math.sin(state.clock.elapsedTime * 1.1)) * 0.28 : 0;

    group.current.position.set(pos.current.x, sitY + walkBob + stretch + celebrate, pos.current.z);
    group.current.rotation.y = THREE.MathUtils.damp(group.current.rotation.y, facing.current, 3.2, dt);
    group.current.rotation.z = THREE.MathUtils.damp(
      group.current.rotation.z,
      moving ? Math.sin(gait) * 0.03 : 0,
      4,
      dt,
    );

    const legL = moving ? Math.sin(gait) * 0.38 : target.sit ? -0.85 : 0;
    const legR = moving ? -Math.sin(gait) * 0.38 : target.sit ? -0.85 : 0;
    if (leftLeg.current) leftLeg.current.rotation.x = THREE.MathUtils.damp(leftLeg.current.rotation.x, legL, 8, dt);
    if (rightLeg.current) rightLeg.current.rotation.x = THREE.MathUtils.damp(rightLeg.current.rotation.x, legR, 8, dt);

    let armLX = 0.12;
    let armRX = 0.12;
    let armLZ = 0;
    let armRZ = 0;
    if (moving) {
      armLX = Math.sin(gait) * 0.28;
      armRX = -Math.sin(gait) * 0.28;
    } else if (target.fun === "stretch") {
      armLX = -2.0;
      armRX = -2.0;
      armLZ = -0.35;
      armRZ = 0.35;
    } else if (target.fun === "celebrate") {
      armLX = -2.1 + Math.sin(state.clock.elapsedTime * 3) * 0.15;
      armRX = -2.1 - Math.sin(state.clock.elapsedTime * 3) * 0.15;
      armLZ = -0.4;
      armRZ = 0.4;
    } else if (target.fun === "smoke") {
      armRX = -1.25 - drag;
      armLX = 0.2;
      armRZ = 0.12;
    } else if (target.fun === "foosball") {
      const spin = Math.sin(state.clock.elapsedTime * 4.5) * 0.28;
      armLX = -0.95 + spin;
      armRX = -0.95 - spin;
    } else if (target.fun === "phone") {
      armRX = -1.55;
      armLX = 0.15;
    } else if (target.fun === "plane") {
      armRX = -1.55 + Math.sin(state.clock.elapsedTime * 1.8) * 0.2;
      armLX = 0.1;
    } else if (target.fun === "nap") {
      armLX = 0.55;
      armRX = 0.55;
    } else if (target.fun === "read") {
      armLX = -0.65;
      armRX = -0.65;
    } else if (target.fun === "sip" || target.holdCup) {
      armRX = -1.25 - sip;
      armLX = 0.18;
    } else if (target.fun === "brew" || target.fun === "microwave") {
      armRX = -1.0;
      armLX = -0.75;
    } else if (target.fun === "board") {
      armRX = -0.95 + Math.sin(state.clock.elapsedTime * 2.2) * 0.12;
      armLX = 0.15;
    } else if (target.fun === "plant") {
      armRX = -0.85;
      armLX = -0.45;
    } else if (agent.state === "working") {
      armLX = -0.85 + type * 6;
      armRX = -0.95 - type * 6;
    }

    if (leftArm.current && rightArm.current) {
      leftArm.current.rotation.x = THREE.MathUtils.damp(leftArm.current.rotation.x, armLX, 6, dt);
      rightArm.current.rotation.x = THREE.MathUtils.damp(rightArm.current.rotation.x, armRX, 6, dt);
      leftArm.current.rotation.z = THREE.MathUtils.damp(leftArm.current.rotation.z, armLZ, 6, dt);
      rightArm.current.rotation.z = THREE.MathUtils.damp(rightArm.current.rotation.z, armRZ, 6, dt);
    }
    if (cup.current) {
      cup.current.visible = target.holdCup || target.fun === "sip" || target.fun === "brew";
      cup.current.position.set(0.26, 0.98 + sip * 0.28, 0.14);
    }
    if (cigarette.current) {
      cigarette.current.visible = target.fun === "smoke";
      cigarette.current.position.set(0.28, 1.08 + drag * 0.2, 0.18);
      cigarette.current.rotation.set(0.2 + drag * 0.35, 0.3, 1.2);
    }
  });

  const lamp =
    agent.state === "working"
      ? C.moss
      : agent.state === "blocked"
        ? C.oxide
        : agent.state === "waiting"
          ? "#b45309"
          : "#6f675e";

  const outfit =
    agent.id === "pm"
      ? { shirt: "#6b2e1a", pants: "#1e1a22", blazer: "#3d2818", shoe: "#1a1410" }
      : agent.id === "backend"
        ? { shirt: "#2a4036", pants: "#1a2330", blazer: null, shoe: "#1c1915" }
        : agent.id === "frontend"
          ? { shirt: "#334a5c", pants: "#2a2430", blazer: null, shoe: "#2a2118" }
          : agent.id === "ai_engineer"
            ? { shirt: "#4a3e28", pants: "#1c2228", blazer: null, shoe: "#1c1915" }
            : { shirt: "#3a5220", pants: "#242028", blazer: null, shoe: "#1a1410" };
  const { shirt, pants, blazer, shoe } = outfit;
  const female = agent.gender === "female";

  return (
    <group ref={group}>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.012, 0]}>
        <circleGeometry args={[0.24, 24]} />
        <meshBasicMaterial color="#1c1915" transparent opacity={0.18} />
      </mesh>

      {/* Legs + shoes (shoes follow gait) */}
      <group ref={leftLeg} position={[-0.09, 0.52, 0]}>
        <mesh position={[0, -0.2, 0]} castShadow>
          <capsuleGeometry args={[0.048, 0.32, 6, 10]} />
          <meshStandardMaterial color={pants} roughness={0.82} />
        </mesh>
        <mesh position={[0, -0.42, 0.03]} castShadow scale={[1, 0.55, 1.4]}>
          <sphereGeometry args={[0.052, 12, 12]} />
          <meshStandardMaterial color={shoe} roughness={0.5} />
        </mesh>
      </group>
      <group ref={rightLeg} position={[0.09, 0.52, 0]}>
        <mesh position={[0, -0.2, 0]} castShadow>
          <capsuleGeometry args={[0.048, 0.32, 6, 10]} />
          <meshStandardMaterial color={pants} roughness={0.82} />
        </mesh>
        <mesh position={[0, -0.42, 0.03]} castShadow scale={[1, 0.55, 1.4]}>
          <sphereGeometry args={[0.052, 12, 12]} />
          <meshStandardMaterial color={shoe} roughness={0.5} />
        </mesh>
      </group>

      {/* Hips / belt */}
      <mesh position={[0, 0.58, 0]} castShadow scale={[1.05, 0.55, 0.85]}>
        <sphereGeometry args={[0.14, 16, 16]} />
        <meshStandardMaterial color={pants} roughness={0.8} />
      </mesh>
      <mesh position={[0, 0.64, 0.11]} castShadow>
        <boxGeometry args={[0.22, 0.03, 0.035]} />
        <meshStandardMaterial color="#3a322c" metalness={0.3} roughness={0.5} />
      </mesh>
      {female ? (
        <mesh position={[0, 0.52, 0]} castShadow scale={[1.15, 0.55, 1.05]}>
          <sphereGeometry args={[0.16, 16, 16]} />
          <meshStandardMaterial color={pants} roughness={0.85} />
        </mesh>
      ) : null}

      {/* Shirt / sweater */}
      <mesh position={[0, 0.88, 0]} castShadow scale={[1.05, 1.15, 0.78]}>
        <capsuleGeometry args={[0.14, 0.22, 6, 14]} />
        <meshStandardMaterial color={shirt} roughness={0.62} />
      </mesh>
      {blazer ? (
        <>
          <mesh position={[-0.1, 0.88, 0.02]} castShadow scale={[0.55, 1.05, 0.7]}>
            <capsuleGeometry args={[0.12, 0.2, 4, 10]} />
            <meshStandardMaterial color={blazer} roughness={0.7} />
          </mesh>
          <mesh position={[0.1, 0.88, 0.02]} castShadow scale={[0.55, 1.05, 0.7]}>
            <capsuleGeometry args={[0.12, 0.2, 4, 10]} />
            <meshStandardMaterial color={blazer} roughness={0.7} />
          </mesh>
        </>
      ) : null}
      {/* Collar + undershirt */}
      <mesh position={[0, 1.08, 0.06]} castShadow>
        <boxGeometry args={[0.15, 0.035, 0.07]} />
        <meshStandardMaterial color={blazer || shirt} roughness={0.55} />
      </mesh>
      <mesh position={[0, 1.05, 0.1]} castShadow>
        <boxGeometry args={[0.045, 0.07, 0.018]} />
        <meshStandardMaterial color="#efe8dc" roughness={0.65} />
      </mesh>

      {/* Shoulders + arms */}
      <mesh position={[-0.18, 1.02, 0]} castShadow scale={[0.7, 0.55, 0.7]}>
        <sphereGeometry args={[0.1, 14, 14]} />
        <meshStandardMaterial color={blazer || shirt} roughness={0.6} />
      </mesh>
      <mesh position={[0.18, 1.02, 0]} castShadow scale={[0.7, 0.55, 0.7]}>
        <sphereGeometry args={[0.1, 14, 14]} />
        <meshStandardMaterial color={blazer || shirt} roughness={0.6} />
      </mesh>
      <group ref={leftArm} position={[-0.22, 1.0, 0]}>
        <mesh position={[0, -0.14, 0]} castShadow>
          <capsuleGeometry args={[0.04, 0.26, 4, 10]} />
          <meshStandardMaterial color={blazer || shirt} roughness={0.6} />
        </mesh>
        <mesh position={[0, -0.32, 0.01]} castShadow>
          <sphereGeometry args={[0.042, 12, 12]} />
          <meshStandardMaterial color={agent.skin} roughness={0.7} />
        </mesh>
      </group>
      <group ref={rightArm} position={[0.22, 1.0, 0]}>
        <mesh position={[0, -0.14, 0]} castShadow>
          <capsuleGeometry args={[0.04, 0.26, 4, 10]} />
          <meshStandardMaterial color={blazer || shirt} roughness={0.6} />
        </mesh>
        <mesh position={[0, -0.32, 0.01]} castShadow>
          <sphereGeometry args={[0.042, 12, 12]} />
          <meshStandardMaterial color={agent.skin} roughness={0.7} />
        </mesh>
      </group>

      {/* Neck + head */}
      <mesh position={[0, 1.16, 0]} castShadow>
        <cylinderGeometry args={[0.055, 0.065, 0.1, 12]} />
        <meshStandardMaterial color={agent.skin} roughness={0.7} />
      </mesh>
      <mesh position={[0, 1.32, 0]} castShadow scale={[0.95, 1.12, 0.92]}>
        <sphereGeometry args={[0.145, 28, 28]} />
        <meshStandardMaterial color={agent.skin} roughness={0.62} />
      </mesh>
      {/* Ears */}
      <mesh position={[-0.13, 1.32, 0]} castShadow scale={[0.45, 0.7, 0.5]}>
        <sphereGeometry args={[0.05, 10, 10]} />
        <meshStandardMaterial color={agent.skin} roughness={0.7} />
      </mesh>
      <mesh position={[0.13, 1.32, 0]} castShadow scale={[0.45, 0.7, 0.5]}>
        <sphereGeometry args={[0.05, 10, 10]} />
        <meshStandardMaterial color={agent.skin} roughness={0.7} />
      </mesh>
      {/* Eyes */}
      <mesh position={[-0.045, 1.34, 0.12]}>
        <sphereGeometry args={[0.022, 10, 10]} />
        <meshStandardMaterial color="#f8f4ef" />
      </mesh>
      <mesh position={[0.045, 1.34, 0.12]}>
        <sphereGeometry args={[0.022, 10, 10]} />
        <meshStandardMaterial color="#f8f4ef" />
      </mesh>
      <mesh position={[-0.045, 1.34, 0.138]}>
        <sphereGeometry args={[0.012, 8, 8]} />
        <meshStandardMaterial color="#2a2118" />
      </mesh>
      <mesh position={[0.045, 1.34, 0.138]}>
        <sphereGeometry args={[0.012, 8, 8]} />
        <meshStandardMaterial color="#2a2118" />
      </mesh>
      {/* Brows */}
      <mesh position={[-0.045, 1.375, 0.125]} rotation={[0, 0, 0.12]}>
        <boxGeometry args={[0.04, 0.008, 0.01]} />
        <meshStandardMaterial color={agent.hair} />
      </mesh>
      <mesh position={[0.045, 1.375, 0.125]} rotation={[0, 0, -0.12]}>
        <boxGeometry args={[0.04, 0.008, 0.01]} />
        <meshStandardMaterial color={agent.hair} />
      </mesh>
      {/* Nose */}
      <mesh position={[0, 1.31, 0.145]} rotation={[0.4, 0, 0]} castShadow>
        <coneGeometry args={[0.018, 0.04, 8]} />
        <meshStandardMaterial color={agent.skin} roughness={0.65} />
      </mesh>
      {/* Mouth */}
      <mesh position={[0, 1.255, 0.13]}>
        <boxGeometry args={[0.04, 0.01, 0.012]} />
        <meshStandardMaterial color="#8a5a4a" roughness={0.7} />
      </mesh>

      {/* Hair */}
      {agent.gender === "female" ? (
        <>
          <mesh position={[0, 1.42, -0.02]} castShadow scale={[1.2, 0.75, 1.15]}>
            <sphereGeometry args={[0.155, 20, 20]} />
            <meshStandardMaterial color={agent.hair} roughness={0.88} />
          </mesh>
          <mesh position={[-0.12, 1.22, -0.02]} castShadow>
            <capsuleGeometry args={[0.055, 0.22, 4, 10]} />
            <meshStandardMaterial color={agent.hair} roughness={0.88} />
          </mesh>
          <mesh position={[0.12, 1.22, -0.02]} castShadow>
            <capsuleGeometry args={[0.055, 0.22, 4, 10]} />
            <meshStandardMaterial color={agent.hair} roughness={0.88} />
          </mesh>
          <mesh position={[0, 1.18, -0.1]} castShadow scale={[1.1, 0.9, 0.7]}>
            <sphereGeometry args={[0.12, 16, 16]} />
            <meshStandardMaterial color={agent.hair} roughness={0.9} />
          </mesh>
        </>
      ) : (
        <>
          <mesh position={[0, 1.42, -0.01]} castShadow scale={[1.08, 0.5, 1.1]}>
            <sphereGeometry args={[0.145, 18, 18]} />
            <meshStandardMaterial color={agent.hair} roughness={0.9} />
          </mesh>
          <mesh position={[0, 1.38, -0.08]} castShadow scale={[1.0, 0.55, 0.7]}>
            <sphereGeometry args={[0.12, 14, 14]} />
            <meshStandardMaterial color={agent.hair} roughness={0.9} />
          </mesh>
        </>
      )}

      {/* Status badge on chest (not a head antenna) */}
      <mesh position={[0.12, 0.95, 0.12]} castShadow>
        <boxGeometry args={[0.07, 0.1, 0.02]} />
        <meshStandardMaterial color="#f3efe6" roughness={0.5} />
      </mesh>
      <mesh position={[0.12, 0.95, 0.132]}>
        <circleGeometry args={[0.022, 12]} />
        <meshStandardMaterial color={lamp} emissive={lamp} emissiveIntensity={0.9} />
      </mesh>

      <group ref={cup} visible={false}>
        <mesh castShadow>
          <cylinderGeometry args={[0.05, 0.045, 0.08, 12]} />
          <meshStandardMaterial color="#f3efe6" />
        </mesh>
        <mesh position={[0, 0.02, 0]}>
          <cylinderGeometry args={[0.035, 0.035, 0.04, 10]} />
          <meshStandardMaterial color="#4a2c1a" />
        </mesh>
      </group>
      <group ref={cigarette} visible={false}>
        <mesh>
          <cylinderGeometry args={[0.012, 0.012, 0.12, 8]} />
          <meshStandardMaterial color="#f3efe6" />
        </mesh>
        <mesh position={[0, 0.05, 0]}>
          <cylinderGeometry args={[0.013, 0.013, 0.03, 8]} />
          <meshStandardMaterial color={C.oxide} emissive={C.oxide} emissiveIntensity={0.5} />
        </mesh>
        <mesh position={[0, -0.05, 0]}>
          <cylinderGeometry args={[0.013, 0.013, 0.025, 8]} />
          <meshStandardMaterial color="#f0c27a" />
        </mesh>
      </group>
      <CigarettePuffs active={Boolean(agent.funLabel?.toLowerCase().includes("smoke"))} />
      {agent.dialogue ? (
        <Html position={[0.18, 1.78, 0]} distanceFactor={8} style={{ pointerEvents: "none" }} zIndexRange={[20, 0]}>
          <div className="office-speech">
            <p>{agent.dialogue}</p>
          </div>
        </Html>
      ) : null}
    </group>
  );
}

function StaffMesh({
  member,
  view,
  index,
  funTime,
}: {
  member: StaffMember;
  view: StaffView;
  index: number;
  funTime: number;
}) {
  const group = useRef<THREE.Group>(null);
  const leftLeg = useRef<THREE.Group>(null);
  const rightLeg = useRef<THREE.Group>(null);
  const leftArm = useRef<THREE.Group>(null);
  const rightArm = useRef<THREE.Group>(null);
  const tray = useRef<THREE.Group>(null);
  const pos = useRef(new THREE.Vector3(member.home.x, 0, member.home.z));
  const facing = useRef(Math.PI);
  const walkPhase = useRef(index * 1.1);
  const funTimeRef = useRef(funTime);
  funTimeRef.current = funTime;

  useFrame((state, delta) => {
    if (!group.current) return;
    const dt = Math.min(delta, 0.05);
    const target = targetForStaff(member, funTimeRef.current, index);
    const goal = new THREE.Vector3(target.x, 0, target.z);
    const toGoal = goal.clone().sub(pos.current);
    const dist = toGoal.length();
    const moving = dist > 0.06;

    if (moving) {
      const step = Math.min(WALK_SPEED * 0.95 * dt, dist);
      toGoal.normalize().multiplyScalar(step);
      pos.current.add(toGoal);
      walkPhase.current += step * 5.2;
      facing.current = Math.atan2(toGoal.x, toGoal.z);
    } else if (typeof target.face === "number") {
      facing.current = target.face;
    } else if (target.faceDesk) {
      facing.current = Math.PI;
    }

    const sitY = target.sit ? 0.3 : 0;
    const gait = walkPhase.current;
    const walkBob = moving ? Math.sin(gait * 2) * 0.012 : 0;
    const serve =
      !moving && (target.duty === "chai" || target.duty === "desk_round")
        ? Math.sin(state.clock.elapsedTime * 1.4) * 0.04
        : 0;

    group.current.position.set(pos.current.x, sitY + walkBob, pos.current.z);
    group.current.rotation.y = THREE.MathUtils.damp(group.current.rotation.y, facing.current, 3.2, dt);
    group.current.rotation.z = THREE.MathUtils.damp(
      group.current.rotation.z,
      moving ? Math.sin(gait) * 0.03 : 0,
      4,
      dt,
    );

    const legL = moving ? Math.sin(gait) * 0.38 : target.sit ? -0.85 : 0;
    const legR = moving ? -Math.sin(gait) * 0.38 : target.sit ? -0.85 : 0;
    if (leftLeg.current) leftLeg.current.rotation.x = THREE.MathUtils.damp(leftLeg.current.rotation.x, legL, 8, dt);
    if (rightLeg.current) rightLeg.current.rotation.x = THREE.MathUtils.damp(rightLeg.current.rotation.x, legR, 8, dt);

    let armLX = 0.12;
    let armRX = 0.12;
    if (moving) {
      armLX = Math.sin(gait) * 0.28;
      armRX = -Math.sin(gait) * 0.28;
    } else if (target.holdTray) {
      armLX = -1.05;
      armRX = -1.05;
    } else if (target.duty === "printer" || target.duty === "files") {
      armRX = -0.9 + Math.sin(state.clock.elapsedTime * 2) * 0.1;
      armLX = -0.5;
    } else if (target.duty === "trash" || target.duty === "snack_restock") {
      armRX = -0.85;
      armLX = -0.7;
    } else if (target.sit) {
      armLX = -0.55;
      armRX = -0.7 + Math.sin(state.clock.elapsedTime * 1.5) * 0.05;
    }

    if (leftArm.current && rightArm.current) {
      leftArm.current.rotation.x = THREE.MathUtils.damp(leftArm.current.rotation.x, armLX, 6, dt);
      rightArm.current.rotation.x = THREE.MathUtils.damp(rightArm.current.rotation.x, armRX, 6, dt);
    }
    if (tray.current) {
      tray.current.visible = Boolean(target.holdTray);
      tray.current.position.set(0, 0.95 + serve, 0.22);
    }
  });

  const { shirt, pants, blazer, shoe } = member;
  const female = member.gender === "female";

  return (
    <group ref={group}>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.012, 0]}>
        <circleGeometry args={[0.24, 24]} />
        <meshBasicMaterial color="#1c1915" transparent opacity={0.18} />
      </mesh>
      <group ref={leftLeg} position={[-0.09, 0.52, 0]}>
        <mesh position={[0, -0.2, 0]} castShadow>
          <capsuleGeometry args={[0.048, 0.32, 6, 10]} />
          <meshStandardMaterial color={pants} roughness={0.82} />
        </mesh>
        <mesh position={[0, -0.42, 0.03]} castShadow scale={[1, 0.55, 1.4]}>
          <sphereGeometry args={[0.052, 12, 12]} />
          <meshStandardMaterial color={shoe} roughness={0.5} />
        </mesh>
      </group>
      <group ref={rightLeg} position={[0.09, 0.52, 0]}>
        <mesh position={[0, -0.2, 0]} castShadow>
          <capsuleGeometry args={[0.048, 0.32, 6, 10]} />
          <meshStandardMaterial color={pants} roughness={0.82} />
        </mesh>
        <mesh position={[0, -0.42, 0.03]} castShadow scale={[1, 0.55, 1.4]}>
          <sphereGeometry args={[0.052, 12, 12]} />
          <meshStandardMaterial color={shoe} roughness={0.5} />
        </mesh>
      </group>
      <mesh position={[0, 0.58, 0]} castShadow scale={[1.05, 0.55, 0.85]}>
        <sphereGeometry args={[0.14, 16, 16]} />
        <meshStandardMaterial color={pants} roughness={0.8} />
      </mesh>
      {female ? (
        <mesh position={[0, 0.52, 0]} castShadow scale={[1.15, 0.55, 1.05]}>
          <sphereGeometry args={[0.16, 16, 16]} />
          <meshStandardMaterial color={pants} roughness={0.85} />
        </mesh>
      ) : null}
      <mesh position={[0, 0.88, 0]} castShadow scale={[1.05, 1.15, 0.78]}>
        <capsuleGeometry args={[0.14, 0.22, 6, 14]} />
        <meshStandardMaterial color={shirt} roughness={0.62} />
      </mesh>
      {blazer ? (
        <>
          <mesh position={[-0.1, 0.88, 0.02]} castShadow scale={[0.55, 1.05, 0.7]}>
            <capsuleGeometry args={[0.12, 0.2, 4, 10]} />
            <meshStandardMaterial color={blazer} roughness={0.7} />
          </mesh>
          <mesh position={[0.1, 0.88, 0.02]} castShadow scale={[0.55, 1.05, 0.7]}>
            <capsuleGeometry args={[0.12, 0.2, 4, 10]} />
            <meshStandardMaterial color={blazer} roughness={0.7} />
          </mesh>
        </>
      ) : null}
      {/* Uniform badge */}
      <mesh position={[0.11, 0.96, 0.12]} castShadow>
        <boxGeometry args={[0.06, 0.08, 0.015]} />
        <meshStandardMaterial color="#efe6d6" />
      </mesh>
      <mesh position={[-0.18, 1.02, 0]} castShadow scale={[0.7, 0.55, 0.7]}>
        <sphereGeometry args={[0.1, 14, 14]} />
        <meshStandardMaterial color={blazer || shirt} roughness={0.6} />
      </mesh>
      <mesh position={[0.18, 1.02, 0]} castShadow scale={[0.7, 0.55, 0.7]}>
        <sphereGeometry args={[0.1, 14, 14]} />
        <meshStandardMaterial color={blazer || shirt} roughness={0.6} />
      </mesh>
      <group ref={leftArm} position={[-0.22, 1.0, 0]}>
        <mesh position={[0, -0.14, 0]} castShadow>
          <capsuleGeometry args={[0.04, 0.26, 4, 10]} />
          <meshStandardMaterial color={blazer || shirt} roughness={0.6} />
        </mesh>
        <mesh position={[0, -0.32, 0.01]} castShadow>
          <sphereGeometry args={[0.042, 12, 12]} />
          <meshStandardMaterial color={member.skin} roughness={0.7} />
        </mesh>
      </group>
      <group ref={rightArm} position={[0.22, 1.0, 0]}>
        <mesh position={[0, -0.14, 0]} castShadow>
          <capsuleGeometry args={[0.04, 0.26, 4, 10]} />
          <meshStandardMaterial color={blazer || shirt} roughness={0.6} />
        </mesh>
        <mesh position={[0, -0.32, 0.01]} castShadow>
          <sphereGeometry args={[0.042, 12, 12]} />
          <meshStandardMaterial color={member.skin} roughness={0.7} />
        </mesh>
      </group>
      <mesh position={[0, 1.16, 0]} castShadow>
        <cylinderGeometry args={[0.055, 0.065, 0.1, 12]} />
        <meshStandardMaterial color={member.skin} roughness={0.7} />
      </mesh>
      <mesh position={[0, 1.32, 0]} castShadow scale={[0.95, 1.12, 0.92]}>
        <sphereGeometry args={[0.145, 28, 28]} />
        <meshStandardMaterial color={member.skin} roughness={0.62} />
      </mesh>
      <mesh position={[-0.045, 1.34, 0.12]}>
        <sphereGeometry args={[0.022, 10, 10]} />
        <meshStandardMaterial color="#f8f4ef" />
      </mesh>
      <mesh position={[0.045, 1.34, 0.12]}>
        <sphereGeometry args={[0.022, 10, 10]} />
        <meshStandardMaterial color="#f8f4ef" />
      </mesh>
      <mesh position={[-0.045, 1.34, 0.138]}>
        <sphereGeometry args={[0.012, 8, 8]} />
        <meshStandardMaterial color="#2a2118" />
      </mesh>
      <mesh position={[0.045, 1.34, 0.138]}>
        <sphereGeometry args={[0.012, 8, 8]} />
        <meshStandardMaterial color="#2a2118" />
      </mesh>
      {female ? (
        <>
          <mesh position={[0, 1.42, -0.02]} castShadow scale={[1.2, 0.75, 1.15]}>
            <sphereGeometry args={[0.155, 20, 20]} />
            <meshStandardMaterial color={member.hair} roughness={0.88} />
          </mesh>
          <mesh position={[-0.12, 1.22, -0.02]} castShadow>
            <capsuleGeometry args={[0.055, 0.22, 4, 10]} />
            <meshStandardMaterial color={member.hair} roughness={0.88} />
          </mesh>
          <mesh position={[0.12, 1.22, -0.02]} castShadow>
            <capsuleGeometry args={[0.055, 0.22, 4, 10]} />
            <meshStandardMaterial color={member.hair} roughness={0.88} />
          </mesh>
        </>
      ) : (
        <mesh position={[0, 1.42, -0.01]} castShadow scale={[1.08, 0.5, 1.1]}>
          <sphereGeometry args={[0.145, 18, 18]} />
          <meshStandardMaterial color={member.hair} roughness={0.9} />
        </mesh>
      )}
      <group ref={tray} visible={false}>
        <mesh castShadow>
          <boxGeometry args={[0.28, 0.02, 0.18]} />
          <meshStandardMaterial color="#3a322c" roughness={0.6} />
        </mesh>
        <mesh position={[-0.06, 0.05, 0]} castShadow>
          <cylinderGeometry args={[0.035, 0.03, 0.07, 10]} />
          <meshStandardMaterial color="#f3efe6" />
        </mesh>
        <mesh position={[0.06, 0.05, 0]} castShadow>
          <cylinderGeometry args={[0.035, 0.03, 0.07, 10]} />
          <meshStandardMaterial color="#f3efe6" />
        </mesh>
        <mesh position={[-0.06, 0.07, 0]}>
          <cylinderGeometry args={[0.022, 0.022, 0.03, 8]} />
          <meshStandardMaterial color="#4a2c1a" />
        </mesh>
        <mesh position={[0.06, 0.07, 0]}>
          <cylinderGeometry args={[0.022, 0.022, 0.03, 8]} />
          <meshStandardMaterial color="#4a2c1a" />
        </mesh>
      </group>
      {view.dialogue ? (
        <Html position={[0.18, 1.78, 0]} distanceFactor={8} style={{ pointerEvents: "none" }} zIndexRange={[20, 0]}>
          <div className="office-speech">
            <p>{view.dialogue}</p>
          </div>
        </Html>
      ) : null}
    </group>
  );
}

function Scene({ agents, funTime }: { agents: AgentView[]; funTime: number }) {
  const byId = useMemo(() => {
    const map = new Map<DeskId, AgentView>();
    for (const agent of agents) map.set(agent.id, agent);
    return map;
  }, [agents]);
  const staff = useMemo(() => floorStaff(funTime), [funTime]);

  const isBrewing =
    agents.some((a) => a.funLabel === "Making coffee") ||
    staff.some((s) => s.duty === "pantry" || s.duty === "chai");
  const isFoosball = agents.some((a) => a.funLabel?.includes("Foosball"));
  const isMicrowave =
    agents.some((a) => a.funLabel?.includes("Heating")) || staff.some((s) => s.duty === "pantry");
  const isPlane = agents.some((a) => a.funLabel?.includes("paper plane"));

  return (
    <>
      <color attach="background" args={[C.fog]} />
      <fog attach="fog" args={[C.fog, 14, 30]} />
      <ambientLight intensity={0.28} />
      <hemisphereLight args={["#fff4e0", "#6a5640", 0.7]} />
      <directionalLight
        castShadow
        position={[6, 12, 4]}
        intensity={1.35}
        shadow-mapSize={[2048, 2048]}
        shadow-camera-far={28}
        shadow-camera-left={-11}
        shadow-camera-right={11}
        shadow-camera-top={11}
        shadow-camera-bottom={-11}
        color="#ffe8c8"
      />
      <directionalLight position={[-4, 6, -6]} intensity={0.45} color="#a8c4d4" />
      <Environment preset="warehouse" environmentIntensity={0.35} />
      <Room brewing={isBrewing} foosball={isFoosball} microwave={isMicrowave} />
      <PaperPlane flying={isPlane} />
      {DESKS.map((desk) => {
        const agent = byId.get(desk.id);
        const mode =
          agent?.state === "working"
            ? "working"
            : agent?.state === "waiting"
              ? "waiting"
              : agent?.state === "blocked"
                ? "blocked"
                : agent
                  ? "idle"
                  : "off";
        return <DeskMesh key={desk.id} desk={desk} mode={mode} />;
      })}
      {DESKS.map((desk, index) => {
        const agent = byId.get(desk.id);
        if (!agent) return null;
        return <AgentMesh key={desk.id} agent={agent} desk={desk} index={index} funTime={funTime} />;
      })}
      {STAFF.map((member, index) => {
        const view = staff.find((s) => s.id === member.id);
        if (!view) return null;
        return <StaffMesh key={member.id} member={member} view={view} index={index} funTime={funTime} />;
      })}
      <ContactShadows position={[0, 0.01, 0]} opacity={0.5} scale={18} blur={2.6} far={10} />
      <OrbitControls
        makeDefault
        enablePan={false}
        autoRotate={false}
        minPolarAngle={0.2}
        maxPolarAngle={1.2}
        minDistance={7}
        maxDistance={22}
        target={[0.3, 0.2, 0]}
      />
    </>
  );
}

export default function OfficeScene3D({
  agents,
  funTime,
}: {
  agents: AgentView[];
  funTime: number;
}) {
  return (
    <div className="office-stage relative mx-auto aspect-[16/10] w-full max-w-6xl overflow-hidden">
      <Canvas
        shadows
        dpr={[1, 1.85]}
        camera={{ position: [0.5, 13.5, 11.5], fov: 38, near: 0.1, far: 70 }}
        gl={{ antialias: true, toneMapping: THREE.ACESFilmicToneMapping }}
        onCreated={({ gl }) => {
          gl.toneMappingExposure = 1.05;
        }}
      >
        <Scene agents={agents} funTime={funTime} />
      </Canvas>
      <div className="office-stage-vignette pointer-events-none absolute inset-0" />
      <p className="pointer-events-none absolute bottom-3 left-4 text-[0.65rem] uppercase tracking-[0.22em] text-[#2a2118]/75">
        Coders Alley · open loft · drag to orbit · scroll to zoom
      </p>
    </div>
  );
}
