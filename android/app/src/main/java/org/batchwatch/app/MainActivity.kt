package org.batchwatch.app

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.core.content.ContextCompat
import org.batchwatch.app.data.local.UserPreferences
import org.batchwatch.app.ui.navigation.BatchWatchNavGraph
import org.batchwatch.app.ui.navigation.Screen
import org.batchwatch.app.ui.theme.BatchWatchTheme

class MainActivity : ComponentActivity() {

    private val notificationPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) {}

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Request notification permission on Android 13+ (API 33+)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                notificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
            }
        }

        val preferences = UserPreferences.create(this)

        setContent {
            BatchWatchTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    val isOnboardingCompleted by preferences.isOnboardingCompleted.collectAsState(initial = null)

                    // Render once DataStore initial value is read
                    isOnboardingCompleted?.let { completed ->
                        val initialScreen = if (completed) Screen.Home else Screen.Onboarding
                        BatchWatchNavGraph(initialScreen = initialScreen)
                    }
                }
            }
        }
    }
}
