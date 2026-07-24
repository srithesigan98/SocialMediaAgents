import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

export const HiSri: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const scale = spring({
    frame,
    fps,
    config: { damping: 12, mass: 0.6 },
  });

  const opacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        background: "linear-gradient(160deg, #1e1b4b 0%, #7c3aed 55%, #f472b6 100%)",
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <div
        style={{
          fontFamily: "Arial, Helvetica, sans-serif",
          fontSize: 160,
          fontWeight: 800,
          color: "white",
          textShadow: "0 8px 40px rgba(0,0,0,0.35)",
          transform: `scale(${scale})`,
          opacity,
        }}
      >
        hi Sri
      </div>
    </AbsoluteFill>
  );
};
