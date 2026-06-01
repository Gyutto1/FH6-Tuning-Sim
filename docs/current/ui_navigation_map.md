# UI Navigation Map (PySide6 Mainline)

## Top-Level Flow

```text
Dashboard
  -> Cars
    -> Car Detail
      -> Build Detail
        -> Tune Detail
          -> Setup Snapshot Confirm
            -> Record Run (Wizard)
  -> Run Library
  -> Tag Library
  -> Settings
```

## Vehicle-Centered Recording Chain

```text
Car -> Build -> Tune -> Setup Snapshot -> Run
```

## Upgrade Store

Single internal state page:

```text
category_grid -> slot_list -> option_list
```

No per-category/per-slot stacked page explosion.

## Tune Detail

Section list first, then section parameter editor:

```text
section_list -> parameter_page(section_id)
```

Back returns to section list.
