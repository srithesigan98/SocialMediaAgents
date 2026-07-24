import { CalculateMetadataFunction, Composition } from "remotion";
import { HiSri } from "./HiSri";

type Props = {};

const calculateMetadata: CalculateMetadataFunction<Props> = () => {
  return {};
};

export const MyComposition = () => {
  return (
    <Composition
      id="MyComp"
      component={MyComponent}
      durationInFrames={60}
      fps={30}
      width={1280}
      height={720}
      calculateMetadata={calculateMetadata}
    />
  );
};

export const HiSriComposition = () => {
  return (
    <Composition
      id="HiSri"
      component={HiSri}
      durationInFrames={90}
      fps={30}
      width={1080}
      height={1920}
    />
  );
};

export const MyComponent: React.FC<Props> = () => {
  return null;
};
