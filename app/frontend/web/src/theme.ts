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
  // Friendly modern: soft, rounded controls on a cool light canvas.
  borderRadiusSmall: "6px",
  borderRadiusMedium: "10px",
  borderRadiusLarge: "14px",
  borderRadiusXLarge: "18px",
  colorNeutralBackground2: "#f6f8fc",
  colorNeutralStroke2: "#e8edf5",
  colorNeutralStroke1: "#d9e0ec",
};
