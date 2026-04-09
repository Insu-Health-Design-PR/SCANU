import { appReducer, createInitialState, normalizeStatus } from "./appStore";

describe("appStore", () => {
  it("normalizes partial status payload", () => {
    const normalized = normalizeStatus({ state: "SCANNING", fused_score: 0.4 });
    expect(normalized.state).toBe("SCANNING");
    expect(normalized.health.sensor_online_count).toBe(0);
  });

  it("keeps score history to rolling window", () => {
    let state = createInitialState();
    state = appReducer(state, {
      type: "UPSERT_STATUS",
      status: normalizeStatus({ state: "IDLE", fused_score: 0.1 }),
      ts: 1_000,
    });
    state = appReducer(state, {
      type: "UPSERT_STATUS",
      status: normalizeStatus({ state: "SCANNING", fused_score: 0.9 }),
      ts: 130_000,
    });

    expect(state.scoreHistory.length).toBe(1);
    expect(state.scoreHistory[0].score).toBe(0.9);
  });
});
