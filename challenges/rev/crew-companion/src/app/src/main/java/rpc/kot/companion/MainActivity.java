package rpc.kot.companion;

import android.app.Activity;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageManager;
import android.graphics.Typeface;
import android.os.Bundle;
import android.text.InputType;
import android.util.Base64;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import java.nio.charset.StandardCharsets;

/**
 * KOT Crew Companion: shift rota, deck map, and the restricted door-code panel.
 *
 * The door-code panel is checked on the handset itself, so it works with the ship
 * network down.
 */
public class MainActivity extends Activity {

    // access code, stored back to front
    private static final String DOOR_CHECK = "4702-TFA-7DLOH";

    private TextView doorOutput;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        int pad = dp(16);
        root.setPadding(pad, pad, pad, pad);

        root.addView(text(getString(R.string.header), 18, true));
        root.addView(text(getString(R.string.shift), 14, false));
        root.addView(text(getString(R.string.deckmap), 14, false));
        root.addView(text(getString(R.string.doors_title), 16, true));

        EditText code = new EditText(this);
        code.setHint(R.string.doors_hint);
        code.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_CAP_CHARACTERS);
        root.addView(code);

        Button unlock = new Button(this);
        unlock.setText(R.string.doors_button);
        root.addView(unlock);

        doorOutput = text("", 14, false);
        root.addView(doorOutput);

        unlock.setOnClickListener((View v) -> {
            if (unlock(code.getText().toString().trim())) {
                doorOutput.setText(revealDoorCodes());
            } else {
                doorOutput.setText(R.string.doors_locked);
            }
        });

        ScrollView scroll = new ScrollView(this);
        scroll.addView(root);
        setContentView(scroll);
    }

    boolean unlock(String code) {
        return new StringBuilder(code).reverse().toString().equals(DOOR_CHECK);
    }

    /** Door codes for this cycle: the bundle is split across the app and joined here. */
    String revealDoorCodes() {
        String bundle = uplinkTag() + getString(R.string.deck_key) + BuildConfig.SHIFT_SIG;
        return new String(Base64.decode(bundle, Base64.DEFAULT), StandardCharsets.UTF_8);
    }

    private String uplinkTag() {
        try {
            ApplicationInfo info = getPackageManager()
                    .getApplicationInfo(getPackageName(), PackageManager.GET_META_DATA);
            return info.metaData.getString("rpc.kot.uplink_tag", "");
        } catch (PackageManager.NameNotFoundException e) {
            return "";
        }
    }

    private TextView text(String s, int sp, boolean bold) {
        TextView t = new TextView(this);
        t.setText(s);
        t.setTextSize(sp);
        t.setPadding(0, dp(6), 0, dp(6));
        t.setTypeface(Typeface.MONOSPACE, bold ? Typeface.BOLD : Typeface.NORMAL);
        return t;
    }

    private int dp(int v) {
        return Math.round(v * getResources().getDisplayMetrics().density);
    }
}
