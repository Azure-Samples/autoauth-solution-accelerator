import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { FluentProvider, mergeClasses, type ButtonState } from "@fluentui/react-components";
import { App } from "./App";
import { azureTheme } from "./theme";
import "./styles.css";

// Fluent v9 has no appearance class, so tag primary buttons for the gradient pill style in styles.css.
const styleHooks = {
  useButtonStyles_unstable: (state: unknown) => {
    const s = state as ButtonState;
    if (s.appearance === "primary") s.root.className = mergeClasses(s.root.className, "btn-primary");
  },
};

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <FluentProvider theme={azureTheme} customStyleHooks_unstable={styleHooks}>
      <App />
    </FluentProvider>
  </StrictMode>,
);
