import { StatusBar } from "expo-status-bar";
import { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { SafeAreaProvider, SafeAreaView } from "react-native-safe-area-context";
import {
  ApiError,
  clearSession,
  loadSavedLots,
  loadSession,
  myLots,
  saveLots,
  saveSession,
  signIn,
  type Lot,
  type Session,
} from "./src/api";

// ScrapLink for Android, first slice: sign in and see your lots, even with no signal.
// The look follows the web client: galvanised grey, safety-yellow buttons, a colour per metal.

const colour = {
  galvanised: "#e8ebe9",
  sheet: "#ffffff",
  ink: "#1c2428",
  inkSoft: "#4a555b",
  rule: "#c5ccc9",
  yellow: "#f2c230",
  held: "#b0352a",
};

const MATERIAL_COLOURS: Record<string, string> = {
  copper: "#b4643a",
  brass: "#c29a2e",
  aluminium: "#a7b2b8",
  steel_hms: "#5b6970",
  cast_iron: "#3a3e41",
  pet_bottles: "#2f7fa8",
  hdpe: "#2f7fa8",
  occ_cardboard: "#a27b4c",
  e_waste_boards: "#2f7347",
  lead_acid_batteries: "#6a4c8c",
};

const STATUS: Record<string, string> = {
  draft: "Not listed yet",
  listed: "Taking bids",
  awarded: "Sold, waiting for payment",
  unsold: "No winning bid",
  funded: "Paid into escrow",
  pickup_scheduled: "Pickup booked",
  delivered: "Weighed",
  settled: "Paid out",
  disputed: "On hold",
};

const kg = (grams: number) => `${(grams / 1000).toLocaleString("en-IN", { maximumFractionDigits: 3 })} kg`;
const rupees = (paise: number) =>
  (paise / 100).toLocaleString("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });

export default function App() {
  const [session, setSession] = useState<Session | null | undefined>(undefined);

  useEffect(() => {
    loadSession().then(setSession, () => setSession(null));
  }, []);

  return (
    <SafeAreaProvider>
      <SafeAreaView style={styles.screen}>
        <StatusBar style="light" />
        <View style={styles.topbar}>
          <Text style={styles.brand}>ScrapLink</Text>
          {session && (
            <Pressable
              accessibilityRole="button"
              onPress={() => void clearSession().then(() => setSession(null))}
            >
              <Text style={styles.topbarLink}>Sign out</Text>
            </Pressable>
          )}
        </View>
        <View style={styles.body}>
          {session === undefined ? (
            <ActivityIndicator style={styles.loading} color={colour.ink} />
          ) : session ? (
            <MyLots session={session} onExpired={() => void clearSession().then(() => setSession(null))} />
          ) : (
            <SignIn
              onSignedIn={(s) => {
                void saveSession(s);
                setSession(s);
              }}
            />
          )}
        </View>
      </SafeAreaView>
    </SafeAreaProvider>
  );
}

function SignIn({ onSignedIn }: { onSignedIn: (session: Session) => void }) {
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      const result = await signIn(phone.trim(), password);
      onSignedIn({ token: result.access_token, user: result.user });
    } catch (err) {
      setError(err instanceof ApiError && err.status === 0 ? "No connection. Try again." : "Wrong phone or password.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <View style={styles.page}>
      <Text style={styles.h1}>Sign in</Text>
      <Text style={styles.label}>Phone number</Text>
      <TextInput
        style={styles.input}
        value={phone}
        onChangeText={setPhone}
        keyboardType="phone-pad"
        autoComplete="tel"
        accessibilityLabel="Phone number"
      />
      <Text style={styles.label}>Password</Text>
      <TextInput
        style={styles.input}
        value={password}
        onChangeText={setPassword}
        secureTextEntry
        accessibilityLabel="Password"
      />
      {error && <Text style={styles.error}>{error}</Text>}
      <Pressable
        accessibilityRole="button"
        disabled={busy || !phone || !password}
        onPress={() => void submit()}
        style={({ pressed }) => [styles.button, (busy || !phone || !password) && styles.disabled, pressed && styles.pressed]}
      >
        <Text style={styles.buttonText}>{busy ? "Signing in…" : "Sign in"}</Text>
      </Pressable>
    </View>
  );
}

function MyLots({ session, onExpired }: { session: Session; onExpired: () => void }) {
  const [lots, setLots] = useState<Lot[] | null>(null);
  const [offlineSince, setOfflineSince] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    try {
      const fresh = await myLots(session.token);
      setLots(fresh);
      setOfflineSince(null);
      await saveLots(fresh);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) return onExpired();
      // No signal or server unreachable: show what was saved last time.
      const saved = await loadSavedLots();
      setLots((current) => current ?? saved?.lots ?? []);
      setOfflineSince(saved?.savedAt ?? "never");
    } finally {
      setRefreshing(false);
    }
  }, [session.token, onExpired]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const title = session.user.role === "buyer" ? "My trades" : "My lots";

  return (
    <FlatList
      contentContainerStyle={styles.page}
      data={lots ?? []}
      keyExtractor={(lot) => lot.id}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => void refresh()} />}
      ListHeaderComponent={
        <>
          <Text style={styles.h1}>{title}</Text>
          <Text style={styles.lede}>{session.user.business_name ?? session.user.name}</Text>
          {offlineSince && (
            <View style={styles.offline} accessibilityRole="alert">
              <Text style={styles.offlineText}>
                {offlineSince === "never"
                  ? "You're offline and nothing is saved on this phone yet."
                  : `You're offline. Showing your lots as of ${new Date(offlineSince).toLocaleString("en-IN", {
                      day: "numeric",
                      month: "short",
                      hour: "numeric",
                      minute: "2-digit",
                    })}.`}
              </Text>
            </View>
          )}
          {lots === null && <ActivityIndicator style={styles.loading} color={colour.ink} />}
        </>
      }
      ListEmptyComponent={lots ? <Text style={styles.empty}>No lots yet.</Text> : null}
      renderItem={({ item }) => <LotRow lot={item} />}
    />
  );
}

function LotRow({ lot }: { lot: Lot }) {
  const grams = lot.measured_weight_grams ?? lot.declared_weight_grams;
  const metal = (lot.material_code && MATERIAL_COLOURS[lot.material_code]) || colour.rule;
  return (
    <View style={[styles.row, { borderLeftColor: metal }]}>
      <Text style={styles.rowName}>
        {lot.material_name ?? "Material not chosen yet"}
        {lot.grade ? `  Grade ${lot.grade}` : ""}
      </Text>
      <Text style={styles.rowDetail}>
        {[grams ? kg(grams) : null, lot.settled_amount_paise != null ? `Paid ${rupees(lot.settled_amount_paise)}` : null]
          .filter(Boolean)
          .join(" · ")}
      </Text>
      <Text style={[styles.rowStatus, lot.status === "disputed" && { color: colour.held }]}>
        {STATUS[lot.status] ?? lot.status}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  // The safe-area bands take the top bar's colour, so the light status bar icons stay visible.
  screen: { flex: 1, backgroundColor: colour.ink },
  body: { flex: 1, backgroundColor: colour.galvanised },
  topbar: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    minHeight: 56,
    paddingHorizontal: 16,
    backgroundColor: colour.ink,
  },
  brand: { color: colour.sheet, fontSize: 22, fontWeight: "800" },
  topbarLink: { color: colour.sheet, fontSize: 16, textDecorationLine: "underline" },
  page: { padding: 16, gap: 10 },
  loading: { marginTop: 24 },
  h1: { fontSize: 32, fontWeight: "800", color: colour.ink, marginBottom: 4 },
  lede: { fontSize: 17, color: colour.inkSoft, marginBottom: 8 },
  label: { fontSize: 17, fontWeight: "600", color: colour.ink, marginTop: 8 },
  input: {
    minHeight: 52,
    paddingHorizontal: 14,
    borderWidth: 2,
    borderColor: colour.rule,
    borderRadius: 8,
    backgroundColor: colour.sheet,
    fontSize: 19,
    color: colour.ink,
  },
  error: { color: colour.held, fontSize: 16, fontWeight: "600" },
  button: {
    minHeight: 52,
    marginTop: 12,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 8,
    borderWidth: 2,
    borderBottomWidth: 6,
    borderColor: colour.ink,
    backgroundColor: colour.yellow,
  },
  pressed: { borderBottomWidth: 2, transform: [{ translateY: 4 }] },
  disabled: { opacity: 0.5 },
  buttonText: { fontSize: 18, fontWeight: "800", color: colour.ink },
  offline: { padding: 12, borderRadius: 8, borderWidth: 2, borderColor: colour.held, backgroundColor: "#fbeae8" },
  offlineText: { color: colour.held, fontSize: 16, fontWeight: "600" },
  empty: { padding: 20, borderWidth: 2, borderStyle: "dashed", borderColor: colour.rule, color: colour.inkSoft },
  row: {
    padding: 14,
    gap: 2,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colour.rule,
    borderLeftWidth: 8,
    backgroundColor: colour.sheet,
  },
  rowName: { fontSize: 18, fontWeight: "700", color: colour.ink },
  rowDetail: { fontSize: 16, color: colour.inkSoft },
  rowStatus: { fontSize: 15, fontWeight: "700", color: colour.ink },
});
