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

    // Increment whenever the bundled MIDlet patch changes. This forces J2ME
    // Loader to rebuild the converted MIDlet while preserving the original
    // game's MIDlet-Version and existing RMS save data.
    private static final String PORT_REVISION = "nom2-port5-ko-s10-r4";
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

        profile.screenWidth = 176;
        profile.screenHeight = 208;
        profile.orientation = 1;
        profile.screenScaleToFit = true;
        profile.screenKeepAspectRatio = true;
        profile.screenScaleType = 1;
        profile.screenScaleRatio = 100;
        profile.screenGravity = 2;
        profile.forceFullscreen = true;
        profile.screenBackgroundColor = 0x000000;
        profile.screenFilter = false;

        // Keep the original pixel-art canvas sharp, but render Korean glyphs
        // with anti-aliasing before the final aspect-fit scale-up.
        profile.fontAA = true;
        profile.fontApplyDimensions = false;
        profile.fontSizeSmall = 9;
        profile.fontSizeMedium = 10;
        profile.fontSizeLarge = 12;

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
