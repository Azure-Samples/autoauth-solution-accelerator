import { Fragment, useEffect, useState, type ReactElement } from "react";
import {
  Avatar,
  Breadcrumb,
  BreadcrumbButton,
  BreadcrumbDivider,
  BreadcrumbItem,
  Button,
  Tooltip,
} from "@fluentui/react-components";
import {
  ArrowResetRegular,
  BranchCompareRegular,
  DataBarVerticalRegular,
  NavigationRegular,
  PeopleRegular,
  QuestionCircleRegular,
  SettingsRegular,
  TaskListSquareLtrRegular,
} from "@fluentui/react-icons";
import { api } from "./api";
import { QueuePage } from "./pages/Queue";
import { CasePage } from "./pages/CaseWorkspace";
import { TracePage } from "./pages/Trace";
import { ProviderPage } from "./pages/Provider";
import { QualityPage } from "./pages/Quality";
import { ParityPage } from "./pages/Parity";

export type Route =
  | { page: "queue" }
  | { page: "case"; id: string }
  | { page: "trace"; id: string }
  | { page: "provider" }
  | { page: "quality" }
  | { page: "parity" };

export function parseRoute(hash: string): Route {
  const parts = hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  if (parts[0] === "case" && parts[1]) {
    return parts[2] === "trace" ? { page: "trace", id: parts[1] } : { page: "case", id: parts[1] };
  }
  if (parts[0] === "provider") return { page: "provider" };
  if (parts[0] === "quality") return { page: "quality" };
  if (parts[0] === "parity") return { page: "parity" };
  return { page: "queue" };
}

export const go = (path: string) => {
  window.location.hash = path;
};

function useRoute(): Route {
  const [route, setRoute] = useState(() => parseRoute(window.location.hash));
  useEffect(() => {
    const onHash = () => setRoute(parseRoute(window.location.hash));
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  return route;
}

type NavItem = { value: Route["page"]; label: string; path: string; icon: ReactElement };

const NAV: NavItem[] = [
  { value: "queue", label: "Reviewer queue", path: "/queue", icon: <TaskListSquareLtrRegular /> },
  { value: "provider", label: "Provider portal", path: "/provider", icon: <PeopleRegular /> },
  { value: "quality", label: "Quality", path: "/quality", icon: <DataBarVerticalRegular /> },
  { value: "parity", label: "Prototype parity", path: "/parity", icon: <BranchCompareRegular /> },
];

function crumbs(route: Route): { label: string; path?: string }[] {
  const root = { label: "AutoAuth", path: "/queue" };
  switch (route.page) {
    case "case":
      return [root, { label: "Reviewer queue", path: "/queue" }, { label: route.id }];
    case "trace":
      return [
        root,
        { label: "Reviewer queue", path: "/queue" },
        { label: route.id, path: `/case/${route.id}` },
        { label: "Trace" },
      ];
    default:
      return [root, { label: NAV.find((n) => n.value === route.page)!.label }];
  }
}

export function App() {
  const route = useRoute();
  const [epoch, setEpoch] = useState(0);
  const [collapsed, setCollapsed] = useState(false);
  const section = route.page === "case" || route.page === "trace" ? "queue" : route.page;
  const trail = crumbs(route);

  const reset = async () => {
    await api.reset();
    setEpoch((n) => n + 1);
    go("/queue");
  };

  return (
    <div className="shell">
      <header className="masthead">
        <Button
          appearance="transparent"
          icon={<NavigationRegular />}
          className="mast-btn"
          aria-label={collapsed ? "Expand navigation" : "Collapse navigation"}
          onClick={() => setCollapsed((c) => !c)}
        />
        <a className="mast-brand" href="#/queue">
          <span className="mast-product">Microsoft Azure</span>
          <span className="mast-sep" />
          <span>AutoAuth</span>
          <span className="mast-tag">Prior authorization</span>
        </a>
        <span className="spacer" />
        <span className="mast-env" title="Offline demo API with fictional patients and the real prototype cases">
          Demo environment
        </span>
        <Tooltip content="Restore the seeded demo cases" relationship="label">
          <Button appearance="transparent" className="mast-btn" icon={<ArrowResetRegular />} onClick={reset}>
            Reset demo
          </Button>
        </Tooltip>
        <Button appearance="transparent" className="mast-btn" icon={<SettingsRegular />} aria-label="Settings" />
        <Button appearance="transparent" className="mast-btn" icon={<QuestionCircleRegular />} aria-label="Help" />
        <span className="mast-user">
          <span className="mast-user-text">
            <span>J. Reviewer</span>
            <span className="mast-user-org">Contoso Health Plan</span>
          </span>
          <Avatar name="J Reviewer" size={28} color="brand" />
        </span>
      </header>
      <div className="body">
        <nav className={`sidenav${collapsed ? " collapsed" : ""}`} aria-label="Main">
          {NAV.map((n) => (
            <Tooltip key={n.value} content={n.label} relationship="label" positioning="after" visible={collapsed ? undefined : false}>
              <a
                href={`#${n.path}`}
                className={`nav-item${section === n.value ? " active" : ""}`}
                aria-current={section === n.value ? "page" : undefined}
                data-nav={n.value}
              >
                <span className="nav-icon">{n.icon}</span>
                <span className="nav-label">{n.label}</span>
              </a>
            </Tooltip>
          ))}
        </nav>
        <main key={epoch}>
          <Breadcrumb aria-label="Breadcrumb" size="small" className="crumbs">
            {trail.map((c, i) => (
              <Fragment key={i}>
                <BreadcrumbItem>
                  <BreadcrumbButton
                    current={i === trail.length - 1}
                    onClick={c.path && i < trail.length - 1 ? () => go(c.path!) : undefined}
                  >
                    {c.label}
                  </BreadcrumbButton>
                </BreadcrumbItem>
                {i < trail.length - 1 ? <BreadcrumbDivider /> : null}
              </Fragment>
            ))}
          </Breadcrumb>
          {route.page === "queue" && <QueuePage />}
          {route.page === "case" && <CasePage key={route.id} id={route.id} />}
          {route.page === "trace" && <TracePage key={route.id} id={route.id} />}
          {route.page === "provider" && <ProviderPage />}
          {route.page === "quality" && <QualityPage />}
          {route.page === "parity" && <ParityPage />}
        </main>
      </div>
    </div>
  );
}
