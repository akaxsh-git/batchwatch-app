package org.batchwatch.app.data.local

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "batchwatch_prefs")

interface UserPreferences {
    val isOnboardingCompleted: Flow<Boolean>
    suspend fun setOnboardingCompleted(completed: Boolean)
    val isSimulateNewAlertEnabled: Flow<Boolean>
    suspend fun setSimulateNewAlert(enabled: Boolean)
    val lastAlertVersion: Flow<String?>
    suspend fun setLastAlertVersion(version: String)

    companion object {
        fun create(context: Context): UserPreferences = UserPreferencesImpl(context)
    }
}

class UserPreferencesImpl(private val context: Context) : UserPreferences {

    private val KEY_ONBOARDING_DONE = booleanPreferencesKey("onboarding_completed")
    private val KEY_SIMULATE_NEW_ALERT = booleanPreferencesKey("simulate_new_alert")
    private val KEY_LAST_ALERT_VERSION = stringPreferencesKey("last_alert_version")

    override val isOnboardingCompleted: Flow<Boolean> = context.dataStore.data.map { prefs ->
        prefs[KEY_ONBOARDING_DONE] ?: false
    }

    override suspend fun setOnboardingCompleted(completed: Boolean) {
        context.dataStore.edit { prefs ->
            prefs[KEY_ONBOARDING_DONE] = completed
        }
    }

    override val isSimulateNewAlertEnabled: Flow<Boolean> = context.dataStore.data.map { prefs ->
        prefs[KEY_SIMULATE_NEW_ALERT] ?: false
    }

    override suspend fun setSimulateNewAlert(enabled: Boolean) {
        context.dataStore.edit { prefs ->
            prefs[KEY_SIMULATE_NEW_ALERT] = enabled
        }
    }

    override val lastAlertVersion: Flow<String?> = context.dataStore.data.map { prefs ->
        prefs[KEY_LAST_ALERT_VERSION]
    }

    override suspend fun setLastAlertVersion(version: String) {
        context.dataStore.edit { prefs ->
            prefs[KEY_LAST_ALERT_VERSION] = version
        }
    }
}
