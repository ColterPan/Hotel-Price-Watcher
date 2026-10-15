import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { MapContainer, Marker, TileLayer, useMap, useMapEvents } from "react-leaflet";

import { estimatePillWidth, placePins } from "../../lib/collision";
import type { HotelView, MapBounds } from "../../lib/view";
import "./map.css";

// OpenStreetMap's standard tiles, darkened in CSS to fit the night theme.
// Fine for personal use under the OSM tile policy; for anything bigger, point
// VITE_TILE_URL at your own or a commercial tile provider (see docs/data-sources.md).
const TILE_URL = import.meta.env.VITE_TILE_URL || "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const ATTRIBUTION =
  import.meta.env.VITE_TILE_ATTRIBUTION ||
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';
const DARKEN = import.meta.env.VITE_TILE_DARKEN !== "false";

const WORLD_VIEW: [number, number] = [12, 105];

interface MapViewProps {
  views: readonly HotelView[];
  center: [number, number] | null;
  /** Changes whenever a new result set arrives, so the map refits once per search. */
  resultsKey: string | null;
  selectedId: string | null;
  hoveredId: string | null;
  maxPriceUsd: number | null;
  formatPrice: (usd: number) => string;
  onSelect: (id: string) => void;
  onHover: (id: string | null) => void;
  onBoundsChange: (bounds: MapBounds) => void;
}

function escapeHtml(text: string): string {
  return text.replace(/[&<>"']/g, (ch) => `&#${ch.charCodeAt(0)};`);
}

interface PinState {
  label: string;
  kind: "live" | "typical" | "none";
  selected: boolean;
  hovered: boolean;
  inBudget: boolean;
  loading: boolean;
  dot: boolean;
}

const iconCache = new Map<string, L.DivIcon>();

function pinIcon(state: PinState): L.DivIcon {
  const classes = [
    "pin",
    `pin--${state.kind}`,
    state.dot ? "pin--dot" : "",
    state.selected ? "pin--selected" : "",
    state.hovered ? "pin--hovered" : "",
    state.inBudget ? "pin--budget" : "",
    state.loading && !state.dot ? "pin--loading" : "",
  ]
    .filter(Boolean)
    .join(" ");
  const text = state.dot ? "" : escapeHtml(state.label);
  const key = `${classes}|${text}`;
  const cached = iconCache.get(key);
  if (cached) return cached;
  const icon = L.divIcon({
    className: "pin-anchor",
    html: `<span class="${classes}">${text}</span>`,
    iconSize: [0, 0],
    iconAnchor: [0, 0],
  });
  iconCache.set(key, icon);
  return icon;
}

function pinLabel(view: HotelView, formatPrice: (usd: number) => string): string {
  if (!view.price) return "?";
  return `${view.price.kind === "typical" ? "~" : ""}${formatPrice(view.price.nightlyUsd)}`;
}

function drawerPadding(): { topLeft: L.PointExpression; bottomRight: L.PointExpression } {
  const wide = window.innerWidth >= 760;
  return wide
    ? { topLeft: [460, 100], bottomRight: [40, 40] }
    : { topLeft: [24, 90], bottomRight: [24, Math.round(window.innerHeight * 0.46)] };
}

function FitToResults({ views, resultsKey, center }: Pick<MapViewProps, "views" | "resultsKey" | "center">) {
  const map = useMap();
  const fittedFor = useRef<string | null>(null);
  useEffect(() => {
    if (!resultsKey || fittedFor.current === resultsKey) return;
    const points = views.map((v) => L.latLng(v.hotel.latitude, v.hotel.longitude));
    const { topLeft, bottomRight } = drawerPadding();
    if (points.length > 1) {
      map.fitBounds(L.latLngBounds(points), { paddingTopLeft: topLeft, paddingBottomRight: bottomRight, maxZoom: 15 });
    } else if (center) {
      map.setView(center, 13);
    }
    fittedFor.current = resultsKey;
  }, [map, views, resultsKey, center]);
  return null;
}

function FollowSelection({ views, selectedId }: Pick<MapViewProps, "views" | "selectedId">) {
  const map = useMap();
  useEffect(() => {
    const selected = views.find((v) => v.hotel.id === selectedId);
    if (!selected) return;
    const point = L.latLng(selected.hotel.latitude, selected.hotel.longitude);
    if (!map.getBounds().pad(-0.15).contains(point)) map.panTo(point);
  }, [map, views, selectedId]);
  return null;
}

/** Priority for keeping a full price pill when pins collide. */
function pinPriority(view: HotelView, selectedId: string | null, hoveredId: string | null): number {
  if (view.hotel.id === selectedId) return 3;
  if (view.hotel.id === hoveredId) return 2;
  return view.value?.value ?? (view.hotel.quality ? view.hotel.quality.score / 20 : -1);
}

function Pins(props: Omit<MapViewProps, "center" | "resultsKey">) {
  const { views, selectedId, hoveredId, maxPriceUsd, formatPrice, onSelect, onHover, onBoundsChange } = props;
  const map = useMap();
  const [viewTick, setViewTick] = useState(0);

  const report = useCallback(() => {
    const b = map.getBounds();
    onBoundsChange({ south: b.getSouth(), west: b.getWest(), north: b.getNorth(), east: b.getEast() });
    setViewTick((t) => t + 1);
  }, [map, onBoundsChange]);
  useMapEvents({ moveend: report, zoomend: report });

  const labels = useMemo(() => new Map(views.map((v) => [v.hotel.id, pinLabel(v, formatPrice)])), [views, formatPrice]);

  const fullPills = useMemo(() => {
    const ordered = [...views].sort(
      (a, b) => pinPriority(b, selectedId, hoveredId) - pinPriority(a, selectedId, hoveredId),
    );
    const boxes = ordered.map((v) => {
      const point = map.latLngToContainerPoint([v.hotel.latitude, v.hotel.longitude]);
      return { id: v.hotel.id, x: point.x, y: point.y, width: estimatePillWidth(labels.get(v.hotel.id) ?? "") };
    });
    return placePins(boxes);
    // viewTick is listed so this reruns after every pan or zoom, since the
    // screen positions it reads from the map change then.
  }, [map, views, labels, selectedId, hoveredId, viewTick]);

  return (
    <>
      {views.map((view) => {
        const { hotel, price } = view;
        const label = labels.get(hotel.id) ?? "?";
        const raised = hotel.id === selectedId || hotel.id === hoveredId;
        const icon = pinIcon({
          label,
          kind: price ? price.kind : "none",
          selected: hotel.id === selectedId,
          hovered: hotel.id === hoveredId,
          inBudget: price !== null && maxPriceUsd !== null && price.nightlyUsd <= maxPriceUsd,
          loading: view.loadingPrice,
          dot: !fullPills.has(hotel.id),
        });
        return (
          <Marker
            key={hotel.id}
            position={[hotel.latitude, hotel.longitude]}
            icon={icon}
            zIndexOffset={raised ? 1000 : fullPills.has(hotel.id) ? 100 : 0}
            title={`${hotel.name}, ${label}`}
            eventHandlers={{
              click: () => onSelect(hotel.id),
              mouseover: () => onHover(hotel.id),
              mouseout: () => onHover(null),
            }}
          />
        );
      })}
    </>
  );
}

function ZoomControlBottomRight() {
  const map = useMap();
  useEffect(() => {
    const control = L.control.zoom({ position: "bottomright" });
    control.addTo(map);
    return () => {
      control.remove();
    };
  }, [map]);
  return null;
}

export function MapView(props: MapViewProps) {
  return (
    <MapContainer
      center={props.center ?? WORLD_VIEW}
      zoom={props.center ? 12 : 4}
      zoomControl={false}
      className={`map ${DARKEN ? "map--darken" : ""}`}
    >
      <TileLayer url={TILE_URL} attribution={ATTRIBUTION} maxZoom={19} />
      <ZoomControlBottomRight />
      <Pins {...props} />
      <FitToResults views={props.views} resultsKey={props.resultsKey} center={props.center} />
      <FollowSelection views={props.views} selectedId={props.selectedId} />
    </MapContainer>
  );
}
