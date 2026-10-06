/*
 * NOM 2 Android port launcher.
 *
 * Original glue code for this repository. It is copied into the Apache-2.0
 * J2ME Loader checkout by tools/prepare_engine.py.
 */
package ru.woesss.j2me.installer;

import android.app.Activity;
import android.content.SharedPreferences;
import android.net.Uri;
import android.os.Bundle;
import android.view.Gravity;
import android.widget.TextView;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;

import io.reactivex.Single;
import io.reactivex.android.schedulers.AndroidSchedulers;
import io.reactivex.schedulers.Schedulers;
import ru.playsoftware.j2meloader.applist.AppItem;
import ru.playsoftware.j2meloader.applist.AppListModel;
import ru.playsoftware.j2meloader.config.Config;
import ru.playsoftware.j2meloader.config.ProfileModel;
import ru.playsoftware.j2meloader.config.ProfilesManager;

public final class Nom2LauncherActivity extends Activity {
    private static final String ASSET_JAR = "nom2/nom2.jar";

    // Change this whenever the bundled MIDlet patch changes. J2ME Loader normally
    // reuses an already-converted MIDlet when MIDlet-Version is unchanged. NOM 2's
    // Korean patch intentionally preserves the original 1.0.43 game version, so a
    // separate port revision is required to force one refresh after APK updates.
    private static final String PORT_REVISION = "nom2-port2-ko-s10-r1";
    private static final String PREFS = "nom2_port_launcher";
    private static final String PREF_INSTALLED_REVISION = "installed_revision";

    private TextView statusView;
    private AppInstaller installer;
    private AppListModel appListModel;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        statusView = new TextView(this);
        statusView.setGravity(Gravity.CENTER);
        statusView.setText("놈2 준비 중...\n" + PORT_REVISION);
        setContentView(statusView);

        try {
            File workRoot = new File(Config.getEmulatorDir());
            if (!workRoot.exists() && !workRoot.mkdirs()) {
                throw new IOException("Cannot create runtime directory: " + workRoot);
            }

            File jar = copyBundledJar();
            appListModel = new AppListModel(getApplication());
            appListModel.getAppRepository().onWorkDirReady();

            installer = new AppInstaller(
                    jar.getAbsolutePath(),
                    Uri.fromFile(jar),
                    getApplication(),
                    appListModel.getAppRepository()
            );
            installOrLaunch();
        } catch (Throwable t) {
            showError(t);
        }
    }

    private boolean bundledRevisionNeedsRefresh() {
        SharedPreferences prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        String installed = prefs.getString(PREF_INSTALLED_REVISION, "");
        return !PORT_REVISION.equals(installed);
    }

    private void markBundledRevisionInstalled() {
        getSharedPreferences(PREFS, MODE_PRIVATE)
                .edit()
                .putString(PREF_INSTALLED_REVISION, PORT_REVISION)
                .apply();
    }

    private void installOrLaunch() {
        final boolean forceRefresh = bundledRevisionNeedsRefresh();

        Single.<Integer>create(installer::loadInfo)
                .subscribeOn(Schedulers.io())
                .flatMap(status -> {
                    if (status == AppInstaller.STATUS_NEW
                            || status == AppInstaller.STATUS_NEWEST
                            || forceRefresh) {
                        return Single.<Integer>create(installer::install);
                    }

                    if (status == AppInstaller.STATUS_EQUAL
                            || status == AppInstaller.STATUS_OLDEST
                            || status == AppInstaller.STATUS_SUCCESS) {
                        return Single.just(status);
                    }

                    return Single.error(new IllegalStateException(
                            "Unsupported installer status: " + status));
                })
                .observeOn(AndroidSchedulers.mainThread())
                .subscribe(ignored -> {
                    markBundledRevisionInstalled();
                    launchGame();
                }, this::showError);
    }

    private File copyBundledJar() throws IOException {
        File dir = new File(getFilesDir(), "nom2");
        if (!dir.exists() && !dir.mkdirs()) {
            throw new IOException("Cannot create NOM 2 asset directory");
        }

        File output = new File(dir, "nom2.jar");
        try (InputStream in = getAssets().open(ASSET_JAR);
             FileOutputStream out = new FileOutputStream(output, false)) {
            byte[] buffer = new byte[16 * 1024];
            int count;
            while ((count = in.read(buffer)) >= 0) {
                out.write(buffer, 0, count);
            }
        }
        return output;
    }

    private void launchGame() {
        try {
            AppItem app = installer.getCurrentApp();
            if (app == null) {
                throw new IllegalStateException("NOM 2 install completed without an app record");
            }

            ensureNom2Profile(app);
            Config.startApp(this, app.getTitle(), app.getPathExt(), false);
            finish();
        } catch (Throwable t) {
            showError(t);
        }
    }

    private void ensureNom2Profile(AppItem app) throws IOException {
        File configDir = new File(Config.getConfigsDir(), app.getPath());
        if (!configDir.exists() && !configDir.mkdirs()) {
            throw new IOException("Cannot create NOM 2 profile directory: " + configDir);
        }

        ProfileModel profile = ProfilesManager.loadConfig(configDir);
        if (profile == null) {
            profile = new ProfileModel(configDir);
        }

        // NOM 2 was authored for the classic 176x208 portrait MIDP canvas.
        profile.screenWidth = 176;
        profile.screenHeight = 208;

        // Galaxy S10 is the primary device target. Keep the complete original
        // image visible and enlarge it to the biggest possible rectangle in
        // either portrait or landscape without stretching or cropping.
        profile.orientation = 1; // FULL_SENSOR in J2ME Loader 1.8.2
        profile.screenScaleToFit = true;
        profile.screenKeepAspectRatio = true;
        profile.screenScaleType = 1;
        profile.screenScaleRatio = 100;
        profile.screenGravity = 2;
        profile.forceFullscreen = true;
        profile.screenBackgroundColor = 0x000000;
        profile.screenFilter = false;

        // Android-native touch handling replaces J2ME Loader's virtual keypad.
        profile.showKeyboard = false;
        profile.touchInput = false;
        profile.graphicsMode = 1;

        if (!ProfilesManager.saveConfig(profile)) {
            throw new IOException("Cannot save NOM 2 runtime profile");
        }
    }

    private void showError(Throwable error) {
        error.printStackTrace();
        runOnUiThread(() -> statusView.setText(
                "놈2 실행 실패.\n\n"
                        + PORT_REVISION
                        + "\n\n"
                        + error.getClass().getSimpleName()
                        + ": "
                        + String.valueOf(error.getMessage())
        ));
    }
}
