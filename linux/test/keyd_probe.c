/* Feed synthetic events to keyd 2.5.0's remapping engine without opening input devices. */
#include "keyd.h"

static struct config config;
static struct keyboard *keyboard;
static int timestamp;

static void ignore_layer(const struct keyboard *kbd, const struct layer *layer, uint8_t active) {}

int load_config(const char *path)
{
    return config_parse(&config, path);
}

void begin_case(void (*record_key)(uint8_t, uint8_t))
{
    struct output output = { .send_key = record_key, .on_layer_change = ignore_layer };
    free(keyboard);
    keyboard = new_keyboard(&config, &output);
    timestamp = 0;
}

void send_event(uint8_t code, uint8_t pressed)
{
    struct key_event event = { .code = code, .pressed = pressed, .timestamp = ++timestamp };
    kbd_process_events(keyboard, &event, 1);
}
