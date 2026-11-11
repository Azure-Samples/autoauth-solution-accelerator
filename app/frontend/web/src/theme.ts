import { createLightTheme, type BrandVariants, type Theme } from "@fluentui/react-components";

// Azure portal blue (#0078D4) at step 80, the slot Fluent uses for primary buttons and links.
const azure: BrandVariants = {
  10: "#020305",
  20: "#0f1a26",
  30: "#102a42",
  40: "#0f365a",
  50: "#0c4372",
  60: "#08518b",
  70: "#035fa5",
  80: "#0078d4",
  90: "#2886de",
  100: "#4a96e3",
  110: "#69a6e8",
  120: "#85b7ec",
  130: "#a0c7f1",
  140: "#bad7f5",
  150: "#d4e7f9",
  160: "#eef6fd",
};

export const azureTheme: Theme = {
  ...createLightTheme(azure),
  // The portal uses near-square controls.
  borderRadiusSmall: "2px",
  borderRadiusMedium: "2px",
  borderRadiusLarge: "4px",
  colorNeutralBackground2: "#faf9f8",
  colorNeutralStroke2: "#edebe9",
};
