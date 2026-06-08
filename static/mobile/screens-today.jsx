/* betsu mobile — Today screen. The day's value bets as cards; tap to place,
 * set your € stake, and (after kickoff) settle. Uses the design system BetCard. */

function PlaceControl({ store, bet }) {
  const r = store.rec(bet.id);
  if (!r.placed) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 14, paddingTop: 14, borderTop: '1px solid var(--border-subtle)' }}>
        <Button variant="secondary" size="sm" icon={<Icon name="circle-plus" size={15} />} onClick={() => store.place(bet.id, true)}>
          Place bet
        </Button>
        <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>suggested {eur(store.suggested(bet))}</span>
      </div>
    );
  }
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 14, paddingTop: 14, borderTop: '1px solid var(--border-subtle)', flexWrap: 'wrap' }}>
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, color: 'var(--win)', fontWeight: 700, fontSize: 13 }}>
        <Icon name="circle-check" size={16} color="var(--win)" /> Placed
      </span>
      <StakeStepper store={store} bet={bet} size="sm" />
      <button onClick={() => store.place(bet.id, false)} style={{ marginLeft: 'auto', border: 'none', background: 'transparent', color: 'var(--text-muted)', fontSize: 12.5, cursor: 'pointer', fontFamily: 'var(--font-sans)', fontWeight: 600, WebkitTapHighlightColor: 'transparent' }}>Remove</button>
    </div>
  );
}

function TodayScreen({ store, variant }) {
  const today = store.today();
  const placedCount = today.filter(b => store.rec(b.id).placed).length;
  const staked = today.reduce((a, b) => a + (store.rec(b.id).placed ? store.rec(b.id).stake : 0), 0);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <ScreenTitle title="today's value bets">
        <p style={{ color: 'var(--text-secondary)', fontSize: 13.5, marginTop: 6, lineHeight: 1.45 }}>
          <b style={{ color: 'var(--text-primary)' }}>{today.length} value bet{today.length === 1 ? '' : 's'}</b> clear{today.length === 1 ? 's' : ''} the 5% edge threshold today{placedCount ? ` · ${placedCount} placed` : ''}{staked ? `, ${eur(staked)} staked` : ''}.
        </p>
      </ScreenTitle>

      {today.length === 0 ? (
        <Panel>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10, textAlign: 'center', padding: '24px 12px' }}>
            <Icon name="moon" size={26} color="var(--warm-400)" />
            <p style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-secondary)' }}>No value bets clear the edge threshold today.</p>
            <p style={{ fontSize: 12.5, color: 'var(--text-muted)' }}>Sitting out. betsu only suggests bets with a real edge.</p>
          </div>
        </Panel>
      ) : (
        today.map((b, i) => (
          <Card key={b.id} highlight={i === 0} padding={0} style={{ overflow: 'hidden' }}>
            {i === 0 ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '10px 16px 0' }}>
                <Icon name="star" size={13} color="var(--gold-600)" />
                <span style={{ fontSize: 10.5, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--gold-700)' }}>Top pick · biggest edge</span>
              </div>
            ) : null}
            <div style={{ padding: '14px 16px 0' }}>
              <BetCard rank={i + 1} top={false} home={b.home} away={b.away} market={b.market}
                pick={b.pick} odds={b.odds} modelProb={b.model} marketProb={b.market_p}
                edge={b.edge} stakeUnits={1} kellyUnits={b.kelly} contextNote={b.note}
                style={{ border: 'none', boxShadow: 'none', padding: 0 }} />
            </div>
            <div style={{ padding: '0 16px 16px' }}><PlaceControl store={store} bet={b} /></div>
          </Card>
        ))
      )}

      <p style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: 12, padding: '4px 0 2px', fontStyle: 'italic' }}>
        Bet responsibly. Only stake what you can afford to lose.
      </p>
    </div>
  );
}

Object.assign(window, { TodayScreen, PlaceControl });
