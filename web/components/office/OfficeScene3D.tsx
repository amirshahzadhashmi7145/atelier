"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import {
  ContactShadows,
  Environment,
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
  SPOTS,
  targetForAgent,
} from "./agentLogic";

function Monitor({ on }: { on: boolean }) {
  return (
    <group position={[-0.35, 0.78, -0.15]}>
      <mesh castShadow position={[0, 0.28, 0]}>
        <boxGeometry args={[0.55, 0.38, 0.04]} />
        <meshStandardMaterial color="#1c1915" roughness={0.4} metalness={0.3} />
      </mesh>
      <mesh position={[0, 0.28, 0.025]}>
        <planeGeometry args={[0.48, 0.3]} />
        <meshStandardMaterial
          color={on ? "#d8e7c8" : "#222"}
          emissive={on ? "#8fbc5a" : "#000"}
          emissiveIntensity={on ? 0.65 : 0}
          roughness={0.35}
        />
      </mesh>
      <mesh position={[0, 0.05, 0.02]} castShadow>
        <boxGeometry args={[0.12, 0.12, 0.08]} />
        <meshStandardMaterial color="#2a2420" />
      </mesh>
    </group>
  );
}

function DeskMesh({ desk, working }: { desk: Desk; working: boolean }) {
  return (
    <group position={[desk.x, 0, desk.z]}>
      <RoundedBox args={[1.85, 0.07, 1.05]} radius={0.02} position={[0, 0.74, 0]} castShadow receiveShadow>
        <meshStandardMaterial color="#7a5535" roughness={0.45} metalness={0.08} />
      </RoundedBox>
      {[
        [-0.78, 0.37, -0.4],
        [0.78, 0.37, -0.4],
        [-0.78, 0.37, 0.4],
        [0.78, 0.37, 0.4],
      ].map((pos, i) => (
        <mesh key={i} position={pos as [number, number, number]} castShadow>
          <cylinderGeometry args={[0.04, 0.05, 0.74, 10]} />
          <meshStandardMaterial color="#3a2a1c" roughness={0.7} />
        </mesh>
      ))}
      <Monitor on={working} />
      <RubberDuck position={[0.55, 0.82, -0.2]} />
      <mesh position={[0.4, 0.79, 0.1]} rotation={[0, -0.25, 0]} castShadow>
        <boxGeometry args={[0.32, 0.015, 0.24]} />
        <meshStandardMaterial color="#f4efe6" roughness={0.95} />
      </mesh>
      {/* nameplate */}
      <mesh position={[0.15, 0.79, 0.35]} castShadow>
        <boxGeometry args={[0.7, 0.02, 0.22]} />
        <meshStandardMaterial color="#2a2420" />
      </mesh>
      <Html position={[0.15, 0.95, 0.35]} center distanceFactor={9} style={{ pointerEvents: "none" }}>
        <div className="min-w-[7rem] rounded-sm border border-[#e3dacd] bg-[#fffaf2]/95 px-2 py-1 text-center shadow-sm">
          <p className="text-[10px] font-semibold leading-tight text-[#1c1915]">{desk.label}</p>
          <p className="text-[9px] text-[#6f675e]">{desk.roleTitle}</p>
        </div>
      </Html>
      <group position={[0, 0, 0.78]}>
        <mesh position={[0, 0.32, 0]} castShadow>
          <boxGeometry args={[0.52, 0.07, 0.48]} />
          <meshStandardMaterial color="#2b2420" roughness={0.7} />
        </mesh>
        <mesh position={[0, 0.58, -0.18]} castShadow>
          <boxGeometry args={[0.52, 0.42, 0.07]} />
          <meshStandardMaterial color="#2b2420" roughness={0.7} />
        </mesh>
        <mesh position={[0, 0.16, 0]} castShadow>
          <cylinderGeometry args={[0.045, 0.045, 0.32, 10]} />
          <meshStandardMaterial color="#1a1614" />
        </mesh>
      </group>
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
      mat.opacity = active ? 0.35 * (1 - rise / 0.55) : 0;
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
      <RoundedBox args={[1.7, 0.95, 0.8]} radius={0.03} position={[0, 0.48, 0]} castShadow receiveShadow>
        <meshStandardMaterial color="#2a221c" roughness={0.65} />
      </RoundedBox>
      {/* machine body */}
      <mesh position={[0.15, 1.15, 0]} castShadow>
        <boxGeometry args={[0.55, 0.7, 0.4]} />
        <meshStandardMaterial color="#3a342e" roughness={0.4} metalness={0.35} />
      </mesh>
      <mesh position={[0.15, 1.45, 0.12]}>
        <boxGeometry args={[0.35, 0.12, 0.08]} />
        <meshStandardMaterial
          color={brewing ? "#3f6212" : "#1c1915"}
          emissive={brewing ? "#3f6212" : "#000"}
          emissiveIntensity={brewing ? 0.6 : 0}
        />
      </mesh>
      {/* portafilter / spout */}
      <mesh position={[0.15, 1.0, 0.22]} castShadow>
        <cylinderGeometry args={[0.04, 0.04, 0.16, 12]} />
        <meshStandardMaterial color="#6b5b4a" metalness={0.4} roughness={0.35} />
      </mesh>
      {/* cup under spout */}
      <mesh position={[0.15, 0.92, 0.28]} castShadow>
        <cylinderGeometry args={[0.07, 0.06, 0.1, 16]} />
        <meshStandardMaterial color="#f3efe6" roughness={0.5} />
      </mesh>
      {brewing ? (
        <mesh position={[0.15, 0.98, 0.28]}>
          <cylinderGeometry args={[0.015, 0.015, 0.12, 6]} />
          <meshStandardMaterial color="#4a2c1a" emissive="#6b3b1f" emissiveIntensity={0.3} />
        </mesh>
      ) : null}
      <Steam active={brewing} />
      {/* grinder */}
      <mesh position={[-0.45, 1.2, 0]} castShadow>
        <cylinderGeometry args={[0.16, 0.18, 0.55, 16]} />
        <meshStandardMaterial color="#4a4036" metalness={0.25} roughness={0.45} />
      </mesh>
      <mesh position={[-0.45, 1.55, 0]} castShadow>
        <sphereGeometry args={[0.14, 16, 16]} />
        <meshStandardMaterial color="#2c241c" transparent opacity={0.55} roughness={0.2} />
      </mesh>
      {/* cups stacked */}
      {[0, 1, 2].map((i) => (
        <mesh key={i} position={[-0.7, 1.0 + i * 0.08, 0.15]} castShadow>
          <cylinderGeometry args={[0.06, 0.05, 0.08, 12]} />
          <meshStandardMaterial color="#efe6d6" />
        </mesh>
      ))}
    </group>
  );
}

function WaterCooler() {
  return (
    <group position={[SPOTS.waterCooler.x, 0, SPOTS.waterCooler.z]}>
      <mesh position={[0, 0.55, 0]} castShadow>
        <boxGeometry args={[0.55, 1.1, 0.45]} />
        <meshStandardMaterial color="#d7d2c6" roughness={0.5} metalness={0.1} />
      </mesh>
      <mesh position={[0, 1.35, 0]} castShadow>
        <sphereGeometry args={[0.28, 20, 20]} />
        <meshStandardMaterial color="#9ec5d4" transparent opacity={0.55} roughness={0.15} />
      </mesh>
      <mesh position={[0.12, 0.85, 0.24]}>
        <boxGeometry args={[0.08, 0.06, 0.1]} />
        <meshStandardMaterial color="#6f675e" />
      </mesh>
    </group>
  );
}

function SnackShelf() {
  return (
    <group position={[SPOTS.snack.x, 0, SPOTS.snack.z]}>
      <mesh position={[0, 0.9, 0]} castShadow>
        <boxGeometry args={[0.7, 1.6, 0.35]} />
        <meshStandardMaterial color="#5c4030" roughness={0.7} />
      </mesh>
      {[0.4, 0.85, 1.3].map((y, i) => (
        <mesh key={i} position={[0, y, 0.05]}>
          <boxGeometry args={[0.6, 0.04, 0.28]} />
          <meshStandardMaterial color="#7a5535" />
        </mesh>
      ))}
      {[0, 1, 2].map((i) => (
        <mesh key={i} position={[-0.15 + i * 0.15, 1.0, 0.1]} castShadow>
          <boxGeometry args={[0.1, 0.14, 0.08]} />
          <meshStandardMaterial color={i === 1 ? "#9a3412" : "#c4a574"} />
        </mesh>
      ))}
    </group>
  );
}

function Whiteboard() {
  return (
    <group position={[-5.4, 1.45, -5.25]}>
      <mesh castShadow>
        <boxGeometry args={[2.2, 1.35, 0.08]} />
        <meshStandardMaterial color="#f8f5ef" roughness={0.35} />
      </mesh>
      <mesh position={[-0.3, 0.15, 0.05]} rotation={[0, 0, -0.1]}>
        <boxGeometry args={[0.9, 0.03, 0.01]} />
        <meshStandardMaterial color="#9a3412" />
      </mesh>
      <mesh position={[0.2, -0.1, 0.05]}>
        <boxGeometry args={[0.7, 0.03, 0.01]} />
        <meshStandardMaterial color="#3f6212" />
      </mesh>
      <mesh position={[0, 0.35, 0.05]} rotation={[0, 0, 0.08]}>
        <boxGeometry args={[1.1, 0.025, 0.01]} />
        <meshStandardMaterial color="#2f4458" />
      </mesh>
    </group>
  );
}

function FoosballTable({ spinning }: { spinning: boolean }) {
  const rods = useRef<THREE.Group>(null);
  useFrame((state) => {
    if (!rods.current) return;
    rods.current.rotation.x = spinning ? state.clock.elapsedTime * 8 : Math.sin(state.clock.elapsedTime) * 0.2;
  });
  return (
    <group position={[SPOTS.foosball.x + 0.4, 0, SPOTS.foosball.z]}>
      <RoundedBox args={[1.8, 0.12, 1.0]} radius={0.02} position={[0, 0.72, 0]} castShadow>
        <meshStandardMaterial color="#3f6212" roughness={0.55} />
      </RoundedBox>
      <mesh position={[0, 0.78, 0]}>
        <boxGeometry args={[1.6, 0.02, 0.85]} />
        <meshStandardMaterial color="#1f3d2b" />
      </mesh>
      {[
        [-0.75, 0.36, -0.4],
        [0.75, 0.36, -0.4],
        [-0.75, 0.36, 0.4],
        [0.75, 0.36, 0.4],
      ].map((pos, i) => (
        <mesh key={i} position={pos as [number, number, number]} castShadow>
          <cylinderGeometry args={[0.04, 0.04, 0.72, 8]} />
          <meshStandardMaterial color="#2a2420" />
        </mesh>
      ))}
      <group ref={rods} position={[0, 0.86, 0]}>
        {[-0.35, 0, 0.35].map((z, i) => (
          <group key={i} position={[0, 0, z]}>
            <mesh rotation={[0, 0, Math.PI / 2]}>
              <cylinderGeometry args={[0.02, 0.02, 1.5, 8]} />
              <meshStandardMaterial color="#c4a574" metalness={0.4} />
            </mesh>
            {[-0.35, 0.35].map((x) => (
              <mesh key={x} position={[x, -0.08, 0]} castShadow>
                <boxGeometry args={[0.06, 0.14, 0.04]} />
                <meshStandardMaterial color={i === 1 ? "#9a3412" : "#f3efe6"} />
              </mesh>
            ))}
          </group>
        ))}
      </group>
      <mesh position={[0, 0.82, 0]}>
        <sphereGeometry args={[0.06, 12, 12]} />
        <meshStandardMaterial color="#f3efe6" />
      </mesh>
    </group>
  );
}

function Microwave({ hot }: { hot: boolean }) {
  return (
    <group position={[SPOTS.microwave.x, 0, SPOTS.microwave.z]}>
      <mesh position={[0, 0.55, 0]} castShadow>
        <boxGeometry args={[0.7, 1.1, 0.45]} />
        <meshStandardMaterial color="#4a4036" roughness={0.6} />
      </mesh>
      <mesh position={[0, 1.25, 0]} castShadow>
        <boxGeometry args={[0.65, 0.4, 0.4]} />
        <meshStandardMaterial color="#2c241c" metalness={0.35} roughness={0.35} />
      </mesh>
      <mesh position={[0, 1.25, 0.21]}>
        <planeGeometry args={[0.45, 0.28]} />
        <meshStandardMaterial
          color={hot ? "#f0c27a" : "#1c1915"}
          emissive={hot ? "#f0c27a" : "#000"}
          emissiveIntensity={hot ? 0.55 : 0}
        />
      </mesh>
    </group>
  );
}

function Beanbag() {
  return (
    <group position={[SPOTS.beanbag.x, 0, SPOTS.beanbag.z]}>
      <mesh position={[0, 0.28, 0]} castShadow scale={[1.1, 0.7, 1.1]}>
        <sphereGeometry args={[0.55, 20, 20]} />
        <meshStandardMaterial color="#9a3412" roughness={0.9} />
      </mesh>
      <mesh position={[-1.2, 0.55, 0.2]} castShadow>
        <boxGeometry args={[0.7, 1.1, 0.25]} />
        <meshStandardMaterial color="#5c4030" />
      </mesh>
      {[0.2, 0.55, 0.9].map((y, i) => (
        <mesh key={i} position={[-1.2, y, 0.1]}>
          <boxGeometry args={[0.55, 0.04, 0.2]} />
          <meshStandardMaterial color="#7a5535" />
        </mesh>
      ))}
      <mesh position={[-1.2, 0.75, 0.18]} castShadow>
        <boxGeometry args={[0.28, 0.08, 0.2]} />
        <meshStandardMaterial color="#f3efe6" />
      </mesh>
    </group>
  );
}

function RubberDuck({ position }: { position: [number, number, number] }) {
  return (
    <group position={position}>
      <mesh castShadow>
        <sphereGeometry args={[0.06, 12, 12]} />
        <meshStandardMaterial color="#e6b422" roughness={0.45} />
      </mesh>
      <mesh position={[0.05, 0.04, 0]} castShadow>
        <sphereGeometry args={[0.035, 10, 10]} />
        <meshStandardMaterial color="#e6b422" />
      </mesh>
      <mesh position={[0.08, 0.04, 0]}>
        <coneGeometry args={[0.015, 0.04, 8]} />
        <meshStandardMaterial color="#9a3412" />
      </mesh>
    </group>
  );
}

function OfficeDog({ beingPetted }: { beingPetted: boolean }) {
  const group = useRef<THREE.Group>(null);
  useFrame((state) => {
    if (!group.current) return;
    const t = state.clock.elapsedTime;
    if (beingPetted) {
      group.current.position.set(SPOTS.pet.x, 0, SPOTS.pet.z);
      group.current.rotation.y = Math.sin(t * 4) * 0.3;
      group.current.position.y = Math.abs(Math.sin(t * 6)) * 0.05;
    } else {
      const x = Math.sin(t * 0.35) * 3.2;
      const z = 1.0 + Math.cos(t * 0.28) * 2.2;
      group.current.position.set(x, 0, z);
      group.current.rotation.y = Math.atan2(
        Math.cos(t * 0.35) * 3.2 * 0.35,
        -Math.sin(t * 0.28) * 2.2 * 0.28,
      );
      group.current.position.y = Math.abs(Math.sin(t * 7)) * 0.03;
    }
  });
  return (
    <group ref={group}>
      <mesh position={[0, 0.28, 0]} castShadow scale={[1.1, 0.7, 0.7]}>
        <sphereGeometry args={[0.28, 16, 16]} />
        <meshStandardMaterial color="#8b6914" roughness={0.85} />
      </mesh>
      <mesh position={[0.28, 0.38, 0]} castShadow>
        <sphereGeometry args={[0.14, 14, 14]} />
        <meshStandardMaterial color="#8b6914" roughness={0.85} />
      </mesh>
      <mesh position={[0.38, 0.4, 0.06]}>
        <sphereGeometry args={[0.025, 8, 8]} />
        <meshStandardMaterial color="#1c1915" />
      </mesh>
      <mesh position={[-0.25, 0.32, 0]} rotation={[0.2, 0, 0.4]} castShadow>
        <capsuleGeometry args={[0.04, 0.18, 4, 8]} />
        <meshStandardMaterial color="#6b4f35" />
      </mesh>
      {[
        [0.12, 0.1, 0.12],
        [0.12, 0.1, -0.12],
        [-0.12, 0.1, 0.12],
        [-0.12, 0.1, -0.12],
      ].map((pos, i) => (
        <mesh key={i} position={pos as [number, number, number]} castShadow>
          <capsuleGeometry args={[0.035, 0.08, 4, 6]} />
          <meshStandardMaterial color="#6b4f35" />
        </mesh>
      ))}
    </group>
  );
}

function SmokePatio() {
  return (
    <group position={[SPOTS.smoke.x - 0.4, 0, SPOTS.smoke.z + 0.2]}>
      {/* patio slab */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.02, 0]} receiveShadow>
        <planeGeometry args={[2.4, 1.8]} />
        <meshStandardMaterial color="#9a8b78" roughness={0.95} />
      </mesh>
      {/* railing / door hint */}
      <mesh position={[1.1, 0.7, -0.7]} castShadow>
        <boxGeometry args={[0.08, 1.4, 1.6]} />
        <meshStandardMaterial color="#6f675e" roughness={0.7} />
      </mesh>
      {/* ashtray stand */}
      <mesh position={[-0.3, 0.45, 0.1]} castShadow>
        <cylinderGeometry args={[0.04, 0.05, 0.9, 10]} />
        <meshStandardMaterial color="#3a342e" metalness={0.3} roughness={0.45} />
      </mesh>
      <mesh position={[-0.3, 0.95, 0.1]} castShadow>
        <cylinderGeometry args={[0.16, 0.14, 0.08, 16]} />
        <meshStandardMaterial color="#2a2420" metalness={0.35} roughness={0.4} />
      </mesh>
      {/* butts */}
      {[0, 1, 2].map((i) => (
        <mesh key={i} position={[-0.35 + i * 0.05, 0.99, 0.08 + (i % 2) * 0.04]} rotation={[0.2, 0.4 * i, 0.3]}>
          <cylinderGeometry args={[0.012, 0.012, 0.05, 6]} />
          <meshStandardMaterial color={i === 1 ? "#f3efe6" : "#4a2c1a"} />
        </mesh>
      ))}
      {/* bench */}
      <mesh position={[0.55, 0.32, 0.35]} castShadow>
        <boxGeometry args={[0.9, 0.08, 0.35]} />
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
        <meshStandardMaterial color="#f3efe6" roughness={0.7} side={THREE.DoubleSide} />
      </mesh>
    </group>
  );
}

function Room({ brewing, foosball, microwave }: { brewing: boolean; foosball: boolean; microwave: boolean }) {
  return (
    <group>
      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <planeGeometry args={[16, 12]} />
        <meshStandardMaterial color="#b89a78" roughness={0.9} />
      </mesh>
      {Array.from({ length: 18 }).map((_, i) => (
        <mesh key={i} rotation={[-Math.PI / 2, 0, 0]} position={[-7.5 + i * 0.9, 0.003, 0]} receiveShadow>
          <planeGeometry args={[0.03, 12]} />
          <meshStandardMaterial color="#a88866" roughness={1} />
        </mesh>
      ))}
      <mesh position={[0, 1.5, -5.5]} receiveShadow>
        <boxGeometry args={[16, 3, 0.25]} />
        <meshStandardMaterial color="#ebe3d4" roughness={0.95} />
      </mesh>
      <mesh position={[-7.9, 1.3, 0]} receiveShadow>
        <boxGeometry args={[0.22, 2.6, 12]} />
        <meshStandardMaterial color="#e4dccb" roughness={0.95} />
      </mesh>
      <mesh position={[7.9, 1.3, 0]} receiveShadow>
        <boxGeometry args={[0.22, 2.6, 12]} />
        <meshStandardMaterial color="#e4dccb" roughness={0.95} />
      </mesh>
      {[-4.5, -1.5, 1.5, 4.5].map((x) => (
        <group key={x} position={[x, 1.75, -5.35]}>
          <mesh>
            <boxGeometry args={[2.1, 1.25, 0.08]} />
            <meshStandardMaterial color="#c9b8a0" roughness={0.5} />
          </mesh>
          <mesh position={[0, 0, 0.05]}>
            <planeGeometry args={[1.85, 1.05]} />
            <meshStandardMaterial
              color="#a9c2d0"
              emissive="#dceaf2"
              emissiveIntensity={0.35}
              roughness={0.15}
            />
          </mesh>
        </group>
      ))}
      <Whiteboard />
      <CoffeeMachine brewing={brewing} />
      <WaterCooler />
      <SnackShelf />
      <FoosballTable spinning={foosball} />
      <Microwave hot={microwave} />
      <Beanbag />
      <SmokePatio />
      {/* rug / stretch zone */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[SPOTS.stretch.x, 0.015, SPOTS.stretch.z]} receiveShadow>
        <circleGeometry args={[1.5, 48]} />
        <meshStandardMaterial color="#cbb89a" roughness={1} />
      </mesh>
      {/* phone booth mark */}
      <mesh position={[SPOTS.phone.x, 0.02, SPOTS.phone.z]} rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[0.45, 24]} />
        <meshStandardMaterial color="#d8cfc0" />
      </mesh>
      <mesh position={[SPOTS.phone.x, 0.9, SPOTS.phone.z - 0.35]} castShadow>
        <boxGeometry args={[0.08, 1.8, 0.08]} />
        <meshStandardMaterial color="#6f675e" />
      </mesh>
      {[
        [-6.5, -3.8],
        [6.5, -3.6],
        [SPOTS.plant.x, SPOTS.plant.z],
      ].map(([x, z], i) => (
        <group key={i} position={[x, 0, z]}>
          <mesh position={[0, 0.22, 0]} castShadow>
            <cylinderGeometry args={[0.2, 0.24, 0.44, 16]} />
            <meshStandardMaterial color="#7d5236" roughness={0.9} />
          </mesh>
          <mesh position={[0, 0.75, 0]} castShadow>
            <sphereGeometry args={[0.42, 20, 20]} />
            <meshStandardMaterial color="#3f6212" roughness={0.8} />
          </mesh>
        </group>
      ))}
      {[-2, 2].map((x) => (
        <mesh key={x} position={[x, 2.85, -1]}>
          <boxGeometry args={[2.2, 0.06, 0.4]} />
          <meshStandardMaterial color="#f5f0e6" emissive="#fff6e8" emissiveIntensity={0.4} />
        </mesh>
      ))}
    </group>
  );
}

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
  const leftLeg = useRef<THREE.Mesh>(null);
  const rightLeg = useRef<THREE.Mesh>(null);
  const leftArm = useRef<THREE.Mesh>(null);
  const rightArm = useRef<THREE.Mesh>(null);
  const cup = useRef<THREE.Group>(null);
  const cigarette = useRef<THREE.Group>(null);
  const smoking = useRef(false);
  const pos = useRef(new THREE.Vector3(desk.x, 0, desk.z + 0.7));
  const facing = useRef(Math.PI);
  const funTimeRef = useRef(funTime);
  funTimeRef.current = funTime;

  useFrame((state, delta) => {
    if (!group.current) return;
    const target = targetForAgent(agent, desk, funTimeRef.current, index);
    smoking.current = target.fun === "smoke";
    const goal = new THREE.Vector3(target.x, 0, target.z);
    pos.current.lerp(goal, 1 - Math.exp(-delta * 4));
    const dist = pos.current.distanceTo(goal);
    const moving = dist > 0.05;

    if (moving) {
      const dir = goal.clone().sub(pos.current);
      facing.current = Math.atan2(dir.x, dir.z);
    } else if (target.faceDesk) {
      facing.current = Math.PI;
    } else if (target.fun === "board" || target.fun === "read" || target.fun === "nap") {
      facing.current = Math.PI;
    } else if (target.fun === "brew" || target.fun === "microwave") {
      facing.current = 0;
    } else if (target.fun === "smoke") {
      facing.current = -0.6 + index * 0.15;
    } else if (target.fun === "foosball") {
      facing.current = index % 2 === 0 ? 0.4 : -0.4;
    }

    const sitY = target.sit ? (target.fun === "nap" ? 0.18 : 0.32) : 0;
    const walkBob = moving ? Math.sin(state.clock.elapsedTime * 9 + index) * 0.03 : 0;
    const stretch =
      target.fun === "stretch" && !moving ? Math.sin(state.clock.elapsedTime * 3) * 0.08 : 0;
    const celebrate =
      target.fun === "celebrate" ? Math.abs(Math.sin(state.clock.elapsedTime * 8)) * 0.22 : 0;
    const type =
      agent.state === "working" && !moving ? Math.sin(state.clock.elapsedTime * 14 + index) * 0.02 : 0;
    const sip =
      (target.fun === "sip" || target.fun === "phone") && !moving
        ? Math.abs(Math.sin(state.clock.elapsedTime * 2)) * 0.25
        : 0;
    const drag =
      target.fun === "smoke" && !moving ? Math.abs(Math.sin(state.clock.elapsedTime * 1.6)) * 0.35 : 0;

    group.current.position.set(pos.current.x, sitY + walkBob + stretch + celebrate, pos.current.z);
    group.current.rotation.y = THREE.MathUtils.damp(group.current.rotation.y, facing.current, 8, delta);

    if (leftLeg.current && rightLeg.current) {
      const swing = moving ? Math.sin(state.clock.elapsedTime * 9 + index) * 0.5 : target.sit ? -0.9 : 0;
      leftLeg.current.rotation.x = swing;
      rightLeg.current.rotation.x = moving ? -swing : target.sit ? -0.9 : 0;
    }
    if (leftArm.current && rightArm.current) {
      if (target.fun === "stretch" && !moving) {
        leftArm.current.rotation.x = -2.2;
        rightArm.current.rotation.x = -2.2;
        leftArm.current.rotation.z = -0.4;
        rightArm.current.rotation.z = 0.4;
      } else if (target.fun === "celebrate" && !moving) {
        leftArm.current.rotation.x = -2.4;
        rightArm.current.rotation.x = -2.4;
        leftArm.current.rotation.z = -0.5;
        rightArm.current.rotation.z = 0.5;
      } else if (target.fun === "smoke" && !moving) {
        rightArm.current.rotation.x = -1.35 - drag;
        leftArm.current.rotation.x = 0.25;
        leftArm.current.rotation.z = 0;
        rightArm.current.rotation.z = 0.15;
      } else if (target.fun === "foosball" && !moving) {
        const spin = Math.sin(state.clock.elapsedTime * 10) * 0.5;
        leftArm.current.rotation.x = -1.0 + spin;
        rightArm.current.rotation.x = -1.0 - spin;
      } else if (target.fun === "phone" && !moving) {
        rightArm.current.rotation.x = -1.6;
        leftArm.current.rotation.x = 0.2;
      } else if (target.fun === "plane" && !moving) {
        rightArm.current.rotation.x = -1.8 + Math.sin(state.clock.elapsedTime * 3) * 0.3;
        leftArm.current.rotation.x = 0.1;
      } else if (target.fun === "pet" && !moving) {
        rightArm.current.rotation.x = -0.7 + Math.sin(state.clock.elapsedTime * 5) * 0.25;
        leftArm.current.rotation.x = 0.2;
      } else if (target.fun === "nap" && !moving) {
        leftArm.current.rotation.x = 0.6;
        rightArm.current.rotation.x = 0.6;
      } else if (target.fun === "read" && !moving) {
        leftArm.current.rotation.x = -0.7;
        rightArm.current.rotation.x = -0.7;
      } else if ((target.fun === "sip" || target.holdCup) && !moving) {
        rightArm.current.rotation.x = -1.4 - sip;
        leftArm.current.rotation.x = 0.2;
        leftArm.current.rotation.z = 0;
        rightArm.current.rotation.z = 0;
      } else if ((target.fun === "brew" || target.fun === "microwave") && !moving) {
        rightArm.current.rotation.x = -1.1;
        leftArm.current.rotation.x = -0.8;
      } else if (target.fun === "board" && !moving) {
        rightArm.current.rotation.x = -1.0 + Math.sin(state.clock.elapsedTime * 4) * 0.2;
        leftArm.current.rotation.x = 0.2;
      } else if (target.fun === "plant" && !moving) {
        rightArm.current.rotation.x = -0.9;
        leftArm.current.rotation.x = -0.5;
      } else if (agent.state === "working" && !moving) {
        leftArm.current.rotation.x = -0.9 + type * 8;
        rightArm.current.rotation.x = -1.0 - type * 8;
        leftArm.current.rotation.z = 0;
        rightArm.current.rotation.z = 0;
      } else if (moving) {
        const a = Math.sin(state.clock.elapsedTime * 9 + index) * 0.45;
        leftArm.current.rotation.x = a;
        rightArm.current.rotation.x = -a;
        leftArm.current.rotation.z = 0;
        rightArm.current.rotation.z = 0;
      } else {
        leftArm.current.rotation.x = 0.15;
        rightArm.current.rotation.x = 0.15;
        leftArm.current.rotation.z = 0;
        rightArm.current.rotation.z = 0;
      }
    }
    if (cup.current) {
      cup.current.visible = target.holdCup || target.fun === "sip" || target.fun === "brew";
      cup.current.position.set(0.28, 0.85 + sip * 0.35, 0.12);
    }
    if (cigarette.current) {
      cigarette.current.visible = target.fun === "smoke";
      cigarette.current.position.set(0.3, 0.95 + drag * 0.25, 0.16);
      cigarette.current.rotation.set(0.2 + drag * 0.4, 0.3, 1.2);
    }
  });

  const lamp =
    agent.state === "working"
      ? "#3f6212"
      : agent.state === "blocked"
        ? "#9a3412"
        : agent.state === "waiting"
          ? "#b45309"
          : "#6f675e";

  return (
    <group ref={group}>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.015, 0]}>
        <circleGeometry args={[0.26, 24]} />
        <meshBasicMaterial color="#1c1915" transparent opacity={0.16} />
      </mesh>
      <mesh ref={leftLeg} position={[-0.09, 0.3, 0]} castShadow>
        <capsuleGeometry args={[0.055, 0.26, 4, 8]} />
        <meshStandardMaterial color="#1c1915" roughness={0.85} />
      </mesh>
      <mesh ref={rightLeg} position={[0.09, 0.3, 0]} castShadow>
        <capsuleGeometry args={[0.055, 0.26, 4, 8]} />
        <meshStandardMaterial color="#1c1915" roughness={0.85} />
      </mesh>
      <mesh position={[0, 0.72, 0]} castShadow>
        <capsuleGeometry args={[0.15, 0.3, 6, 14]} />
        <meshStandardMaterial color={agent.color} roughness={0.5} />
      </mesh>
      <mesh ref={leftArm} position={[-0.22, 0.78, 0]} castShadow>
        <capsuleGeometry args={[0.045, 0.22, 4, 8]} />
        <meshStandardMaterial color={agent.color} roughness={0.5} />
      </mesh>
      <mesh ref={rightArm} position={[0.22, 0.78, 0]} castShadow>
        <capsuleGeometry args={[0.045, 0.22, 4, 8]} />
        <meshStandardMaterial color={agent.color} roughness={0.5} />
      </mesh>
      <mesh position={[0, 1.12, 0]} castShadow>
        <sphereGeometry args={[0.17, 24, 24]} />
        <meshStandardMaterial color={agent.skin} roughness={0.65} />
      </mesh>
      {agent.gender === "female" ? (
        <>
          <mesh position={[0, 1.22, -0.02]} castShadow scale={[1.15, 0.7, 1.05]}>
            <sphereGeometry args={[0.18, 18, 18]} />
            <meshStandardMaterial color={agent.hair} roughness={0.85} />
          </mesh>
          <mesh position={[-0.14, 1.08, 0.02]} castShadow>
            <sphereGeometry args={[0.07, 12, 12]} />
            <meshStandardMaterial color={agent.hair} roughness={0.85} />
          </mesh>
          <mesh position={[0.14, 1.08, 0.02]} castShadow>
            <sphereGeometry args={[0.07, 12, 12]} />
            <meshStandardMaterial color={agent.hair} roughness={0.85} />
          </mesh>
        </>
      ) : (
        <mesh position={[0, 1.24, -0.01]} castShadow scale={[1.05, 0.45, 1.05]}>
          <sphereGeometry args={[0.16, 16, 16]} />
          <meshStandardMaterial color={agent.hair} roughness={0.9} />
        </mesh>
      )}
      <mesh position={[0, 1.36, 0]}>
        <sphereGeometry args={[0.045, 12, 12]} />
        <meshStandardMaterial color={lamp} emissive={lamp} emissiveIntensity={0.7} />
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
          <meshStandardMaterial color="#9a3412" emissive="#9a3412" emissiveIntensity={0.45} />
        </mesh>
        <mesh position={[0, -0.05, 0]}>
          <cylinderGeometry args={[0.013, 0.013, 0.025, 8]} />
          <meshStandardMaterial color="#f0c27a" />
        </mesh>
      </group>
      <CigarettePuffs active={Boolean(agent.funLabel?.includes("smoke on the patio"))} />
      {agent.dialogue ? (
        <Html position={[0.15, 1.7, 0]} distanceFactor={8} style={{ pointerEvents: "none" }} zIndexRange={[20, 0]}>
          <div className="office-speech">
            <p>{agent.dialogue}</p>
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

  const isBrewing = agents.some((a) => a.funLabel === "Brewing a pour-over");
  const isFoosball = agents.some((a) => a.funLabel?.includes("Foosball"));
  const isMicrowave = agents.some((a) => a.funLabel?.includes("Reheating"));
  const isPetting = agents.some((a) => a.funLabel?.includes("dog"));
  const isPlane = agents.some((a) => a.funLabel?.includes("paper plane"));

  return (
    <>
      <color attach="background" args={["#cfc3ae"]} />
      <fog attach="fog" args={["#cfc3ae", 16, 32]} />
      <ambientLight intensity={0.35} />
      <hemisphereLight args={["#fff6ea", "#8a7355", 0.65]} />
      <directionalLight
        castShadow
        position={[5, 11, 3]}
        intensity={1.5}
        shadow-mapSize={[2048, 2048]}
        shadow-camera-far={28}
        shadow-camera-left={-10}
        shadow-camera-right={10}
        shadow-camera-top={10}
        shadow-camera-bottom={-10}
      />
      <pointLight position={[-2, 2.6, -1]} intensity={0.4} color="#fff1d6" />
      <pointLight position={[2, 2.6, -1]} intensity={0.4} color="#fff1d6" />
      <Environment preset="apartment" environmentIntensity={0.45} />
      <Room brewing={isBrewing} foosball={isFoosball} microwave={isMicrowave} />
      <OfficeDog beingPetted={isPetting} />
      <PaperPlane flying={isPlane} />
      {DESKS.map((desk) => (
        <DeskMesh key={desk.id} desk={desk} working={byId.get(desk.id)?.state === "working"} />
      ))}
      {DESKS.map((desk, index) => {
        const agent = byId.get(desk.id);
        if (!agent) return null;
        return <AgentMesh key={desk.id} agent={agent} desk={desk} index={index} funTime={funTime} />;
      })}
      <ContactShadows position={[0, 0.01, 0]} opacity={0.45} scale={18} blur={2.8} far={10} />
      <OrbitControls
        makeDefault
        enablePan={false}
        minPolarAngle={0.55}
        maxPolarAngle={1.25}
        minDistance={7}
        maxDistance={16}
        target={[0.5, 0.4, -0.5]}
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
    <div className="relative mx-auto aspect-[16/11] w-full max-w-5xl overflow-hidden rounded-sm border border-[color:var(--color-line)] bg-[#cfc3ae]">
      <Canvas
        shadows
        dpr={[1, 1.75]}
        camera={{ position: [7.5, 7.2, 8.5], fov: 36, near: 0.1, far: 60 }}
        gl={{ antialias: true }}
      >
        <Scene agents={agents} funTime={funTime} />
      </Canvas>
      <p className="pointer-events-none absolute bottom-3 left-3 text-[0.65rem] uppercase tracking-[0.2em] text-[#3f3124]/80">
        Coders Alley · drag to look around
      </p>
    </div>
  );
}
