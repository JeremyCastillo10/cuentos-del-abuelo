import React from "react";
import type { Ambiente } from "./tipos";

// Siluetas negras del lugar, dibujadas en un lienzo de 1080x1920.
// Todo es geometría propia: no hay imágenes de terceros.
const NEGRO = "#020203";

const pino = (x: number, base: number, alto: number, k: number) => {
  const ancho = alto * 0.42;
  return (
    <polygon
      key={k}
      fill={NEGRO}
      points={`${x},${base - alto} ${x - ancho / 2},${base} ${x + ancho / 2},${base}`}
    />
  );
};

const Bosque: React.FC = () => (
  <g>
    {/* Fila de atrás, más clara, para dar profundidad */}
    {[0, 130, 260, 390, 520, 650, 780, 910, 1040].map((x, k) => (
      <polygon
        key={`f${k}`}
        fill="#16291f"
        points={`${x + 40},${1380 - 520 - (k % 3) * 90} ${x - 60},${1420} ${x + 140},${1420}`}
      />
    ))}
    {[
      [60, 1500, 760], [200, 1560, 980], [330, 1520, 640], [470, 1600, 820],
      [620, 1540, 700], [760, 1580, 1000], [900, 1520, 720], [1030, 1560, 900],
    ].map(([x, b, a], k) => pino(x, b, a, k))}
    <rect x={0} y={1500} width={1080} height={420} fill={NEGRO} />
  </g>
);

const Casa: React.FC<{ luz: number }> = ({ luz }) => (
  <g>
    <rect x={0} y={1560} width={1080} height={360} fill={NEGRO} />
    <polygon fill={NEGRO} points="250,1580 250,1080 540,820 830,1080 830,1580" />
    <rect x={690} y={860} width={70} height={190} fill={NEGRO} />
    {/* Ventanas: una con luz que parpadea */}
    <rect x={330} y={1150} width={120} height={150} fill={`rgba(255,200,110,${0.55 * luz})`} />
    <rect x={630} y={1150} width={120} height={150} fill="#0b0b10" />
    <rect x={480} y={1360} width={120} height={220} fill="#0b0b10" />
    {/* Árbol seco */}
    <path d="M110 1580 L130 1250 L80 1150 M130 1250 L190 1120 M125 1330 L60 1290" stroke={NEGRO} strokeWidth={22} fill="none" strokeLinecap="round" />
  </g>
);

const Carretera: React.FC<{ t: number }> = ({ t }) => (
  <g>
    <polygon fill="#0a0a0e" points="0,1920 1080,1920 600,1250 480,1250" />
    {Array.from({ length: 6 }, (_, i) => {
      const k = ((i + (t / 40) % 1) / 6) ** 2;
      const y = 1250 + k * 670;
      const w = 6 + k * 40;
      return <rect key={i} x={540 - w / 2} y={y} width={w} height={10 + k * 60} fill="rgba(230,220,180,0.55)" />;
    })}
    <rect x={0} y={1180} width={1080} height={80} fill={NEGRO} />
    {[120, 300, 820, 990].map((x, k) => pino(x, 1260, 380 + (k % 2) * 160, k))}
  </g>
);

const Mar: React.FC<{ t: number }> = ({ t }) => (
  <g>
    {Array.from({ length: 5 }, (_, i) => {
      const y = 1330 + i * 120;
      const fase = t / (30 - i * 3) + i;
      const d = Array.from({ length: 13 }, (_, j) => {
        const x = j * 90;
        return `${j === 0 ? "M" : "L"}${x} ${y + Math.sin(fase + j * 0.8) * (10 + i * 4)}`;
      }).join(" ");
      return <path key={i} d={`${d} L1080 1920 L0 1920 Z`} fill={i === 4 ? NEGRO : `rgba(2,4,8,${0.5 + i * 0.12})`} />;
    })}
    {/* Faro */}
    <polygon fill={NEGRO} points="880,1340 900,1000 940,1000 960,1340" />
    <rect x={895} y={960} width={50} height={45} fill="rgba(255,230,160,0.7)" />
  </g>
);

const Pueblo: React.FC<{ luz: number }> = ({ luz }) => (
  <g>
    {[
      [0, 1330, 220], [200, 1270, 180], [370, 1360, 230], [590, 1250, 200], [780, 1330, 160], [930, 1290, 150],
    ].map(([x, y, w], k) => (
      <g key={k}>
        <rect x={x} y={y} width={w} height={1920 - y} fill={NEGRO} />
        <polygon fill={NEGRO} points={`${x - 10},${y} ${x + w / 2},${y - 90} ${x + w + 10},${y}`} />
        {k % 2 === 0 && <rect x={x + w / 2 - 25} y={y + 70} width={50} height={60} fill={`rgba(255,190,100,${0.5 * luz})`} />}
      </g>
    ))}
    {/* Iglesia */}
    <rect x={480} y={1000} width={60} height={260} fill={NEGRO} />
    <rect x={505} y={950} width={10} height={60} fill={NEGRO} />
    <rect x={490} y={965} width={40} height={10} fill={NEGRO} />
  </g>
);

const Cementerio: React.FC = () => (
  <g>
    <path d="M0 1500 Q540 1430 1080 1500 L1080 1920 L0 1920 Z" fill={NEGRO} />
    {[90, 250, 420, 610, 780, 950].map((x, k) => {
      const y = 1470 - (k % 3) * 25;
      return k % 2 === 0 ? (
        <g key={k}>
          <rect x={x - 12} y={y - 150} width={24} height={170} fill={NEGRO} />
          <rect x={x - 55} y={y - 115} width={110} height={24} fill={NEGRO} />
        </g>
      ) : (
        <path key={k} d={`M${x - 55} ${y + 20} L${x - 55} ${y - 80} Q${x} ${y - 150} ${x + 55} ${y - 80} L${x + 55} ${y + 20} Z`} fill={NEGRO} />
      );
    })}
    <path d="M980 1480 L960 1150 L900 1060 M960 1150 L1030 1040 M962 1260 L1050 1230" stroke={NEGRO} strokeWidth={20} fill="none" strokeLinecap="round" />
  </g>
);

const Habitacion: React.FC<{ luz: number }> = ({ luz }) => (
  <g>
    {/* Ventana con la luna detrás */}
    <rect x={340} y={520} width={400} height={560} fill="none" stroke={NEGRO} strokeWidth={34} />
    <line x1={540} y1={520} x2={540} y2={1080} stroke={NEGRO} strokeWidth={22} />
    <line x1={340} y1={800} x2={740} y2={800} stroke={NEGRO} strokeWidth={22} />
    <rect x={0} y={0} width={340} height={1920} fill={NEGRO} opacity={0.92} />
    <rect x={740} y={0} width={340} height={1920} fill={NEGRO} opacity={0.92} />
    <rect x={0} y={1080} width={1080} height={840} fill={NEGRO} opacity={0.95} />
    {/* Cama y puerta entreabierta con luz */}
    <rect x={120} y={1500} width={560} height={160} rx={30} fill="#000" />
    <rect x={850} y={1120} width={120} height={520} fill={`rgba(255,210,150,${0.25 * luz})`} />
  </g>
);

const Ciudad: React.FC<{ luz: number }> = ({ luz }) => (
  <g>
    {[
      [0, 1050, 160], [150, 1180, 140], [280, 900, 170], [440, 1120, 130], [560, 980, 180], [730, 1200, 120], [840, 1000, 240],
    ].map(([x, y, w], k) => (
      <g key={k}>
        <rect x={x} y={y} width={w} height={1920 - y} fill={NEGRO} />
        {Array.from({ length: 8 }, (_, j) =>
          (j * 7 + k * 3) % 5 === 0 ? (
            <rect key={j} x={x + 20 + (j % 3) * 40} y={y + 50 + Math.floor(j / 3) * 90} width={22} height={34} fill={`rgba(255,220,140,${0.45 * luz})`} />
          ) : null,
        )}
      </g>
    ))}
    {/* Farola */}
    <rect x={150} y={1380} width={14} height={540} fill={NEGRO} />
    <circle cx={157} cy={1375} r={26} fill={`rgba(255,210,140,${0.7 * luz})`} />
  </g>
);

export const Siluetas: React.FC<{ ambiente: Ambiente; t: number; luz: number }> = ({ ambiente, t, luz }) => {
  switch (ambiente) {
    case "bosque": return <Bosque />;
    case "casa": return <Casa luz={luz} />;
    case "carretera": return <Carretera t={t} />;
    case "mar": return <Mar t={t} />;
    case "pueblo": return <Pueblo luz={luz} />;
    case "cementerio": return <Cementerio />;
    case "habitacion": return <Habitacion luz={luz} />;
    case "ciudad": return <Ciudad luz={luz} />;
  }
};
